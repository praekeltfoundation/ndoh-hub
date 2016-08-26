import requests
import json
import uuid

from django.conf import settings
from celery.task import Task
from celery.utils.log import get_task_logger
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient  # noqa

from ndoh_hub import utils
from .models import Registration, SubscriptionRequest


is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL,
    auth_token=settings.IDENTITY_STORE_TOKEN
)


def get_risk_status(reg_type, mom_dob, edd):
    """ Determine the risk level of the mother """

    # high risk if postbirth registration
    if "postbirth" in reg_type:
        return "high"

    # high risk if age < 18
    age = utils.get_mom_age(utils.get_today(), mom_dob)
    if age < 18:
        return "high"

    # high risk if registering after 20 weeks pregnant
    weeks = utils.get_pregnancy_week(utils.get_today(), edd)
    if weeks >= 20:
        return "high"

    # otherwise normal risk
    return "normal"


class ValidateSubscribe(Task):
    """ Task to validate a registration model entry's registration
    data.
    """
    name = "ndoh_hub.registrations.tasks.validate_subscribe"
    l = get_task_logger(__name__)

    # Validation checks
    def check_lang(self, data_fields, registration):
        if "language" not in data_fields:
            return ["Language is missing from data"]
        elif not utils.is_valid_lang(registration.data["language"]):
            return ["Language not a valid option"]
        else:
            return []

    def check_mom_dob(self, data_fields, registration):
        if "mom_dob" not in data_fields:
            return ["Mother DOB missing"]
        elif not utils.is_valid_date(registration.data["mom_dob"]):
            return ["Mother DOB invalid"]
        else:
            return []

    def check_edd(self, data_fields, registration):
        if "edd" not in data_fields:
            return ["Estimated Due Date missing"]
        elif not utils.is_valid_date(registration.data["edd"]):
            return ["Estimated Due Date invalid"]
        else:
            return []

    def check_baby_dob(self, data_fields, registration):
        if "baby_dob" not in data_fields:
            return ["Baby Date of Birth missing"]
        elif not utils.is_valid_date(registration.data["baby_dob"]):
            return ["Baby Date of Birth invalid"]
        elif utils.get_baby_age(utils.get_today(),
                                registration.data["baby_dob"]) < 0:
            return ["Baby Date of Birth cannot be in the future"]
        else:
            return []

    def check_operator_id(self, data_fields, registration):
        if "operator_id" not in data_fields:
            return ["Operator ID missing"]
        elif not utils.is_valid_uuid(registration.data["operator_id"]):
            return ["Operator ID invalid"]
        else:
            return []

    def check_msisdn_registrant(self, data_fields, registration):
        if "msisdn_registrant" not in data_fields:
            return ["MSISDN of Registrant missing"]
        elif not utils.is_valid_msisdn(registration.data["msisdn_registrant"]):
            return ["MSISDN of Registrant invalid"]
        else:
            return []

    def check_msisdn_device(self, data_fields, registration):
        if "msisdn_device" not in data_fields:
            return ["MSISDN of device missing"]
        elif not utils.is_valid_msisdn(registration.data["msisdn_device"]):
            return ["MSISDN of device invalid"]
        else:
            return []

    def check_faccode(self, data_fields, registration):
        if "faccode" not in data_fields:
            return ["Facility (clinic) code missing"]
        elif not utils.is_valid_faccode(registration.data["faccode"]):
            return ["Facility code invalid"]
        else:
            return []

    def check_consent(self, data_fields, registration):
        if "consent" not in data_fields:
            return ["Consent is missing"]
        elif registration.data["consent"] is not True:
            return ["Cannot continue without consent"]
        else:
            return []

    def check_sa_id_no(self, data_fields, registration):
        if "sa_id_no" not in data_fields:
            return ["SA ID number missing"]
        elif not utils.is_valid_sa_id_no(registration.data["sa_id_no"]):
            return ["SA ID number invalid"]
        else:
            return []

    def check_passport_no(self, data_fields, registration):
        if "passport_no" not in data_fields:
            return ["Passport number missing"]
        elif not utils.is_valid_passport_no(registration.data["passport_no"]):
            return ["Passport number invalid"]
        else:
            return []

    def check_passport_origin(self, data_fields, registration):
        if "passport_origin" not in data_fields:
            return ["Passport origin missing"]
        elif not utils.is_valid_passport_origin(
          registration.data["passport_origin"]):
            return ["Passport origin invalid"]
        else:
            return []

    def check_id(self, data_fields, registration):
        if "id_type" not in data_fields:
            return ["ID type missing"]
        elif registration.data["id_type"] not in ["sa_id", "passport", "none"]:
            return ["ID type should be 'sa_id', 'passport' or 'none'"]
        else:
            id_errors = []
            if registration.data["id_type"] == "sa_id":
                id_errors += self.check_sa_id_no(data_fields, registration)
                id_errors += self.check_mom_dob(data_fields, registration)
            elif registration.data["id_type"] == "passport":
                id_errors += self.check_passport_no(data_fields, registration)
                id_errors += self.check_passport_origin(
                    data_fields, registration)
            elif registration.data["id_type"] == "none":
                id_errors += self.check_mom_dob(data_fields, registration)
            return id_errors

    # Validate
    def validate(self, registration):
        """ Validates that all the required info is provided for a
        registration.
        """
        self.l.info("Starting registration validation")

        validation_errors = []

        # Check if registrant_id is a valid UUID
        if not utils.is_valid_uuid(registration.registrant_id):
            validation_errors += ["Invalid UUID registrant_id"]

        # Check that required fields are provided and valid
        data_fields = registration.data.keys()

        if registration.reg_type == "pmtct_prebirth":
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_edd(data_fields, registration)
            validation_errors += self.check_operator_id(
                data_fields, registration)

        elif registration.reg_type == "pmtct_postbirth":
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_baby_dob(data_fields, registration)
            validation_errors += self.check_operator_id(
                data_fields, registration)

        elif registration.reg_type == "nurseconnect":
            validation_errors += self.check_faccode(
                data_fields, registration)
            validation_errors += self.check_operator_id(
                data_fields, registration)
            validation_errors += self.check_msisdn_registrant(
                data_fields, registration)
            validation_errors += self.check_msisdn_device(
                data_fields, registration)
            validation_errors += self.check_lang(
                data_fields, registration)

        elif registration.reg_type == "momconnect_prebirth":
            validation_errors += self.check_operator_id(
                data_fields, registration)
            validation_errors += self.check_msisdn_registrant(
                data_fields, registration)
            validation_errors += self.check_msisdn_device(
                data_fields, registration)
            validation_errors += self.check_lang(
                data_fields, registration)
            validation_errors += self.check_edd(
                data_fields, registration)
            validation_errors += self.check_faccode(
                data_fields, registration)
            validation_errors += self.check_consent(
                data_fields, registration)
            validation_errors += self.check_id(
                data_fields, registration)

        elif registration.reg_type == "momconnect_postbirth":
            validation_errors.append("Momconnect postbirth not yet supported")

        elif registration.reg_type == "loss_general":
            validation_errors.append("Loss general not yet supported")

        # Evaluate if there were any problems, save and return
        if len(validation_errors) == 0:
            self.l.info("Registration validated successfully - updating "
                        "registration object")
            registration.validated = True
            registration.save()
            self.l.info("Registration object updated.")
            return True
        else:
            self.l.info("Registration validation failed - updating "
                        "registration object")
            registration.data["invalid_fields"] = validation_errors
            registration.save()
            self.l.info("Registration object updated.")
            return False

    # Create SubscriptionRequest
    def create_subscriptionrequests(self, registration):
        """ Create SubscriptionRequest(s) based on the
        validated registration.
        """
        self.l.info("Starting subscriptionrequest creation")

        self.l.info("Calculating weeks")
        weeks = 1  # default week number

        # . calculate weeks along
        if (registration.reg_type == "momconnect_prebirth" and
           registration.source.authority not in ["hw_partial", "patient"]):
            weeks = utils.get_pregnancy_week(utils.get_today(),
                                             registration.data["edd"])

        elif registration.reg_type == "pmtct_prebirth":
            weeks = utils.get_pregnancy_week(utils.get_today(),
                                             registration.data["edd"])

        elif registration.reg_type == "pmtct_postbirth":
            weeks = utils.get_baby_age(utils.get_today(),
                                       registration.data["baby_dob"])

        # . determine messageset shortname
        self.l.info("Determining messageset shortname")
        short_name = utils.get_messageset_short_name(
            registration.reg_type, registration.source.authority, weeks)

        # . determine sbm details
        self.l.info("Determining SBM details")
        msgset_id, msgset_schedule, next_sequence_number =\
            utils.get_messageset_schedule_sequence(
                short_name, weeks)

        subscription = {
            "identity": registration.registrant_id,
            "messageset": msgset_id,
            "next_sequence_number": next_sequence_number,
            "lang": registration.data["language"],
            "schedule": msgset_schedule
        }
        self.l.info("Creating SubscriptionRequest object")
        SubscriptionRequest.objects.create(**subscription)
        self.l.info("SubscriptionRequest created")

        return "SubscriptionRequest created"

    # Set risk status
    def set_risk_status(self, registration):
        """ Determine the risk status of the mother and save it to her identity
        """
        self.l.info("Calculating risk level")
        risk = get_risk_status(registration.reg_type,
                               registration.data["mom_dob"],
                               registration.data["edd"])
        self.l.info("Reading the identity")
        identity = is_client.get_identity(registration.registrant_id)
        details = identity["details"]

        if "pmtct" in details:
            details["pmtct"]["risk_status"] = risk
        else:
            details["pmtct"] = {"risk_status": risk}

        self.l.info("Saving risk level to the identity")
        is_client.update_identity(
            registration.registrant_id, {"details": details})

        self.l.info("Identity updated with risk level")
        return risk

    # Run
    def run(self, registration_id, **kwargs):
        """ Sets the registration's validated field to True if
        validation is successful.
        """
        self.l = self.get_logger(**kwargs)
        self.l.info("Looking up the registration")
        registration = Registration.objects.get(id=registration_id)

        reg_validates = self.validate(registration)

        if reg_validates:
            self.create_subscriptionrequests(registration)
            self.set_risk_status(registration)
            self.l.info("Task executed successfully")
            return True
        else:
            self.l.info("Task terminated due to validation issues")
            return False


validate_subscribe = ValidateSubscribe()


class DeliverHook(Task):
    def run(self, target, payload, instance_id=None, hook_id=None, **kwargs):
        """
        target:     the url to receive the payload.
        payload:    a python primitive data structure
        instance_id:   a possibly None "trigger" instance ID
        hook_id:       the ID of defining Hook object
        """
        requests.post(
            url=target,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token %s' % settings.HOOK_AUTH_TOKEN
            }
        )


def deliver_hook_wrapper(target, payload, instance, hook):
    if instance is not None:
        if isinstance(instance.id, uuid.UUID):
            instance_id = str(instance.id)
        else:
            instance_id = instance.id
    else:
        instance_id = None
    kwargs = dict(target=target, payload=payload,
                  instance_id=instance_id, hook_id=hook.id)
    DeliverHook.apply_async(kwargs=kwargs)
