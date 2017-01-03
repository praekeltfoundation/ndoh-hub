import json
import uuid
from datetime import datetime

import requests
from requests.exceptions import HTTPError

from django.conf import settings
from celery.task import Task
from celery.utils.log import get_task_logger
from go_http.metrics import MetricsApiClient
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.service_rating import ServiceRatingApiClient

from ndoh_hub import utils


is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL,
    auth_token=settings.IDENTITY_STORE_TOKEN
)

sr_client = ServiceRatingApiClient(
    api_url=settings.SERVICE_RATING_URL,
    auth_token=settings.SERVICE_RATING_TOKEN
)


def get_metric_client(session=None):
    return MetricsApiClient(
        auth_token=settings.METRICS_AUTH_TOKEN,
        api_url=settings.METRICS_URL,
        session=session)


class FireMetric(Task):

    """ Fires a metric using the MetricsApiClient
    """
    name = "registrations.tasks.fire_metric"

    def run(self, metric_name, metric_value, session=None, **kwargs):
        metric_value = float(metric_value)
        metric = {
            metric_name: metric_value
        }
        metric_client = get_metric_client(session=session)
        metric_client.fire(metric)
        return "Fired metric <%s> with value <%s>" % (
            metric_name, metric_value)

fire_metric = FireMetric()


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
            # Checks that apply to clinic, chw, public
            validation_errors += self.check_operator_id(
                data_fields, registration)
            validation_errors += self.check_msisdn_registrant(
                data_fields, registration)
            validation_errors += self.check_msisdn_device(
                data_fields, registration)
            validation_errors += self.check_lang(
                data_fields, registration)
            validation_errors += self.check_consent(
                data_fields, registration)

            # Checks that apply to clinic, chw
            if registration.source.authority in ["hw_full", "hw_partial"]:
                validation_errors += self.check_id(
                    data_fields, registration)

            # Checks that apply to clinic only
            if registration.source.authority == "hw_full":
                validation_errors += self.check_edd(
                    data_fields, registration)
                validation_errors += self.check_faccode(
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
        from .models import SubscriptionRequest
        SubscriptionRequest.objects.create(**subscription)
        self.l.info("SubscriptionRequest created")

        return "SubscriptionRequest created"

    # Create ServiceRating Invite
    def create_servicerating_invite(self, registration):
        """ Create a new servicerating invite
        """
        invite_data = {
            "identity": registration.registrant_id
            # could provide "invite" to override servicerating defaults
        }
        self.l.info("Creating ServiceRating invite")
        response = sr_client.create_invite(invite_data)
        self.l.info("Created ServiceRating invite")
        return response

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

    def send_to_jembi(self, registration):
        """
        Runs the correct task to send the registration information to
        Jembi.
        """
        task = BasePushRegistrationToJembi.get_jembi_task_for_registration(
            registration)
        return task.delay(registration_id=str(registration.pk))

    # Run
    def run(self, registration_id, **kwargs):
        """ Sets the registration's validated field to True if
        validation is successful.
        """
        self.l = self.get_logger(**kwargs)
        self.l.info("Looking up the registration")
        from .models import Registration
        registration = Registration.objects.get(id=registration_id)

        reg_validates = self.validate(registration)
        if reg_validates:
            self.create_subscriptionrequests(registration)

            # NOTE: disable service rating for now
            # if registration.reg_type == "momconnect_prebirth" and\
            #    registration.source.authority == "hw_full":
            #     self.create_servicerating_invite(registration)

            if "pmtct" in registration.reg_type:
                self.set_risk_status(registration)

            self.l.info("Scheduling registration push to Jembi")
            self.send_to_jembi(registration)

            self.l.info("Task executed successfully")
            return True
        else:
            self.l.info("Task terminated due to validation issues")
            return False


validate_subscribe = ValidateSubscribe()


class BasePushRegistrationToJembi(object):
    """
    Base class that contains helper functions for pushing registration data
    to Jembi.
    """
    name = "ndoh_hub.registrations.tasks.base_push_registration_to_jembi"
    l = get_task_logger(__name__)

    def get_patient_id(self, id_type, id_no=None,
                       passport_origin=None, mom_msisdn=None):
        if id_type == 'sa_id':
            return id_no + "^^^ZAF^NI"
        elif id_type == 'passport':
            return id_no + '^^^' + passport_origin.upper() + '^PPN'
        else:
            return mom_msisdn.replace('+', '') + '^^^ZAF^TEL'

    def get_dob(self, mom_dob):
        if mom_dob is not None:
            return mom_dob.strftime("%Y%m%d")
        else:
            return None

    def get_today(self):
        return datetime.today()

    def get_timestamp(self):
        return self.get_today().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def get_jembi_task_for_registration(registration):
        """
        NOTE:   this is a convenience method for getting the relevant
                Jembi task to fire for a registration.
        """
        if registration.reg_type in ('nurseconnect',):
            return push_nurse_registration_to_jembi
        if "pmtct" in registration.reg_type:
            return push_pmtct_registration_to_jembi
        return push_registration_to_jembi

    @staticmethod
    def get_authority_from_source(source):
        """
        NOTE:   this is a convenience method to map the new "source"
                back to ndoh-control's "authority" fields to maintain
                backwards compatibility with existing APIs
        """
        if source.name.startswith('EXTERNAL CHW'):
            # catch all external chw sources
            return 'chw'
        else:
            return {
                'PUBLIC USSD App': 'personal',
                'OPTOUT USSD App': 'optout',
                'CLINIC USSD App': 'clinic',
                'CHW USSD App': 'chw',
                'NURSE USSD App': 'nurse',
                'PMTCT USSD App': 'pmtct',
            }.get(source.name)

    def run(self, registration_id, **kwargs):
        from .models import Registration
        registration = Registration.objects.get(pk=registration_id)
        authority = self.get_authority_from_source(registration.source)
        if authority is None:
            self.l.error(
                'Unable to establish authority for source %s. Skipping.' % (
                    registration.source))
            return

        json_doc = self.build_jembi_json(registration)
        try:
            result = requests.post(
                self.URL,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            result.raise_for_status()
            return result.text
        except (HTTPError,) as e:
            # retry message sending if in 500 range (3 default retries)
            if 500 < e.response.status_code < 599:
                raise self.retry(exc=e)
            else:
                self.l.error('Error when posting to Jembi. Payload: %r' % (
                    json_doc))
                raise e
        except (Exception,) as e:
            self.l.error(
                'Problem posting Registration %s JSON to Jembi' % (
                    registration_id), exc_info=True)


class PushRegistrationToJembi(BasePushRegistrationToJembi, Task):
    """ Task to push registration data to Jembi
    """
    name = "ndoh_hub.registrations.tasks.push_registration_to_jembi"
    l = get_task_logger(__name__)
    URL = "%s/subscription" % settings.JEMBI_BASE_URL

    def get_subscription_type(self, authority):
        authority_map = {
            'personal': 1,
            'chw': 2,
            'clinic': 3,
            'optout': 4,
            # NOTE: these are other valid values recognised by Jembi but
            #       currently not used by us.
            # 'babyloss': 5,
            # 'servicerating': 6,
            # 'helpdesk': 7,
            'pmtct': 9,
        }
        return authority_map[authority]

    def transform_language_code(self, lang):
        return {
            'zul_ZA': 'zu',
            'xho_ZA': 'xh',
            'afr_ZA': 'af',
            'eng_ZA': 'en',
            'nso_ZA': 'nso',
            'tsn_ZA': 'tn',
            'sot_ZA': 'st',
            'tso_ZA': 'ts',
            'ssw_ZA': 'ss',
            'ven_ZA': 've',
            'nbl_ZA': 'nr',
        }[lang]

    def build_jembi_json(self, registration):
        """ Compile json to be sent to Jembi. """
        self.l.info("Compiling Jembi Json data for PushRegistrationToJembi")
        authority = self.get_authority_from_source(registration.source)
        json_template = {
            "mha": registration.data.get('mha', 1),
            "swt": registration.data.get('swt', 1),
            "dmsisdn": registration.data.get('msisdn_device'),
            "cmsisdn": registration.data.get('msisdn_registrant'),
            "id": self.get_patient_id(
                registration.data.get('id_type'),
                (registration.data.get('sa_id_no')
                 if registration.data.get('id_type') == 'sa_id'
                 else registration.data.get('passport_no')),
                # passport_origin may be None if sa_id is used
                registration.data.get('passport_origin'),
                registration.data.get('msisdn_registrant')),
            "type": self.get_subscription_type(authority),
            "lang": self.transform_language_code(
                registration.data['language']),
            "encdate": registration.data.get('encdate', self.get_timestamp()),
            "faccode": registration.data.get('faccode'),
            "dob": (self.get_dob(
                datetime.strptime(registration.data['mom_dob'], '%Y-%m-%d'))
                    if registration.data.get('mom_dob')
                    else None)
        }

        # Self registrations on all lines should use cmsisdn as dmsisdn too
        if registration.data.get('msisdn_device') is None:
            json_template["dmsisdn"] = registration.data.get(
                'msisdn_registrant')

        if authority == 'clinic':
            json_template["edd"] = datetime.strptime(
                registration.data["edd"], '%Y-%m-%d').strftime("%Y%m%d")

        return json_template


push_registration_to_jembi = PushRegistrationToJembi()


class PushPmtctRegistrationToJembi(PushRegistrationToJembi, Task):
    """ Task to push PMTCT registration data to Jembi
    """
    name = "ndoh_hub.registrations.tasks.push_pmtct_registration_to_jembi"
    URL = "%s/pmtctSubscription" % settings.JEMBI_BASE_URL

push_pmtct_registration_to_jembi = PushPmtctRegistrationToJembi()


class PushNurseRegistrationToJembi(BasePushRegistrationToJembi, Task):
    name = "ndoh_hub.registrations.tasks.push_nurse_registration_to_jembi"
    l = get_task_logger(__name__)
    URL = "%s/nc/subscription" % settings.JEMBI_BASE_URL

    def get_persal(self, identity):
        details = identity['details']
        return details.get('nurseconnect', {}).get('persal_no')

    def get_sanc(self, identity):
        details = identity['details']
        return details.get('nurseconnect', {}).get('sanc_reg_no')

    def build_jembi_json(self, registration):
        """
        Compiles and returns a dictionary representing the JSON that should
        be sent to Jembi for the given registration.
        """
        self.l.info(
            "Compiling Jembi Json data for PushNurseRegistrationToJembi")
        identity = is_client.get_identity(registration.registrant_id)
        json_template = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": registration.data['msisdn_device'],
            "cmsisdn": registration.data['msisdn_registrant'],
            # NOTE: this likely needs to be updated to reflect a change
            #       in msisdn as `rmsisdn` stands for replacement msisdn
            "rmsisdn": None,
            "faccode": registration.data['faccode'],
            "id": self.get_patient_id(
                registration.data.get('id_type'),
                (registration.data.get('sa_id_no')
                 if registration.data.get('id_type') == 'sa_id'
                 else registration.data.get('passport_no')),
                # passport_origin may be None if sa_id is used
                registration.data.get('passport_origin'),
                registration.data['msisdn_registrant']),
            "dob": (self.get_dob(
                datetime.strptime(registration.data['mom_dob'], '%Y-%m-%d'))
                    if registration.data.get('mom_db')
                    else None),
            "persal": self.get_persal(identity),
            "sanc": self.get_sanc(identity),
            "encdate": self.get_timestamp(),
        }

        return json_template

push_nurse_registration_to_jembi = PushNurseRegistrationToJembi()


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
