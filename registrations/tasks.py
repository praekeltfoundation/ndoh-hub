import json
import random
import re
import uuid
from datetime import datetime
from functools import partial

import phonenumbers
import requests
from celery import chain
from celery.exceptions import SoftTimeLimitExceeded
from celery.task import Task
from celery.utils.log import get_task_logger
from demands import HTTPServiceError
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import translation
from requests.exceptions import ConnectionError, HTTPError, RequestException
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.service_rating import ServiceRatingApiClient
from wabclient.exceptions import AddressException

from ndoh_hub import utils
from ndoh_hub.celery import app

from .models import Registration, Source, WhatsAppContact

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL, auth_token=settings.IDENTITY_STORE_TOKEN
)

sr_client = ServiceRatingApiClient(
    api_url=settings.SERVICE_RATING_URL, auth_token=settings.SERVICE_RATING_TOKEN
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


class HTTPRetryMixin(object):
    """
    A mixin for exponential delay retries on retriable http errors
    """

    max_retries = 10
    delay_factor = 1
    jitter_percentage = 0.25

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        delay = (2 ** self.request.retries) * self.delay_factor
        delay *= 1 + (random.random() * self.jitter_percentage)
        if (
            isinstance(exc, HTTPError)
            and self.request.retries < self.max_retries
            and 500 <= exc.response.status_code < 600
        ):
            raise self.retry(countdown=delay, exc=exc)
        if isinstance(exc, ConnectionError) and self.request.retries < self.max_retries:
            raise self.retry(countdown=delay, exc=exc)


class ValidateSubscribe(Task):
    """ Task to validate a registration model entry's registration
    data.
    """

    name = "ndoh_hub.registrations.tasks.validate_subscribe"
    log = get_task_logger(__name__)

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
        elif not utils.is_valid_edd(registration.data["edd"]):
            return ["Estimated Due Date invalid"]
        else:
            return []

    def check_baby_dob(self, data_fields, registration):
        if "baby_dob" not in data_fields:
            return ["Baby Date of Birth missing"]
        elif not utils.is_valid_date(registration.data["baby_dob"]):
            return ["Baby Date of Birth invalid"]
        elif utils.get_baby_age(utils.get_today(), registration.data["baby_dob"]) < 0:
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
        elif not utils.is_valid_passport_origin(registration.data["passport_origin"]):
            return ["Passport origin invalid"]
        else:
            return []

    def check_id(self, data_fields, registration):
        if "id_type" not in data_fields:
            return ["ID type missing"]
        elif not utils.is_valid_id_type(registration.data["id_type"]):
            return ["ID type should be one of {}".format(utils.ID_TYPES)]
        else:
            id_errors = []
            if registration.data["id_type"] == "sa_id":
                id_errors += self.check_sa_id_no(data_fields, registration)
                id_errors += self.check_mom_dob(data_fields, registration)
            elif registration.data["id_type"] == "passport":
                id_errors += self.check_passport_no(data_fields, registration)
                id_errors += self.check_passport_origin(data_fields, registration)
            elif registration.data["id_type"] == "none":
                id_errors += self.check_mom_dob(data_fields, registration)
            return id_errors

    # Validate
    def validate(self, registration):
        """ Validates that all the required info is provided for a
        registration.
        """
        self.log.info("Starting registration validation")

        validation_errors = []

        # Check if registrant_id is a valid UUID
        if not utils.is_valid_uuid(registration.registrant_id):
            validation_errors += ["Invalid UUID registrant_id"]

        # Check that required fields are provided and valid
        data_fields = registration.data.keys()

        if "pmtct_prebirth" in registration.reg_type:
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_edd(data_fields, registration)
            validation_errors += self.check_operator_id(data_fields, registration)

        elif "pmtct_postbirth" in registration.reg_type:
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_baby_dob(data_fields, registration)
            validation_errors += self.check_operator_id(data_fields, registration)

        elif "nurseconnect" in registration.reg_type:
            validation_errors += self.check_faccode(data_fields, registration)
            validation_errors += self.check_operator_id(data_fields, registration)
            validation_errors += self.check_msisdn_registrant(data_fields, registration)
            validation_errors += self.check_msisdn_device(data_fields, registration)
            validation_errors += self.check_lang(data_fields, registration)

        elif registration.reg_type in ["momconnect_prebirth", "whatsapp_prebirth"]:
            # Checks that apply to clinic, chw, public
            validation_errors += self.check_operator_id(data_fields, registration)
            validation_errors += self.check_msisdn_registrant(data_fields, registration)
            validation_errors += self.check_msisdn_device(data_fields, registration)
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_consent(data_fields, registration)

            # Checks that apply to clinic, chw
            if registration.source.authority in ["hw_full", "hw_partial"]:
                validation_errors += self.check_id(data_fields, registration)

            # Checks that apply to clinic only
            if registration.source.authority == "hw_full":
                validation_errors += self.check_edd(data_fields, registration)
                validation_errors += self.check_faccode(data_fields, registration)

        elif registration.reg_type in ("momconnect_postbirth", "whatsapp_postbirth"):
            if registration.source.authority == "hw_full":
                validation_errors += self.check_operator_id(data_fields, registration)
                validation_errors += self.check_msisdn_registrant(
                    data_fields, registration
                )
                validation_errors += self.check_msisdn_device(data_fields, registration)
                validation_errors += self.check_lang(data_fields, registration)
                validation_errors += self.check_consent(data_fields, registration)
                validation_errors += self.check_id(data_fields, registration)
                validation_errors += self.check_baby_dob(data_fields, registration)
                validation_errors += self.check_faccode(data_fields, registration)
            else:
                validation_errors += [
                    "Momconnect postbirth not yet supported for public or CHW"
                ]

        elif registration.reg_type == "loss_general":
            validation_errors.append("Loss general not yet supported")

        # Evaluate if there were any problems, save and return
        if len(validation_errors) == 0:
            self.log.info(
                "Registration validated successfully - updating " "registration object"
            )
            registration.validated = True
            registration.save()
            self.log.info("Registration object updated.")
            return True
        else:
            self.log.info(
                "Registration validation failed - updating " "registration object"
            )
            registration.data["invalid_fields"] = validation_errors
            registration.save()
            self.log.info("Registration object updated.")
            return False

    def create_popi_subscriptionrequest(self, registration):
        """
        Creates a new subscription request for the POPI message set. This
        message set tells the user how to access the POPI required services.
        This should only be sent for Clinic or CHW registrations.
        """
        if registration.reg_type not in (
            "momconnect_prebirth",
            "momconnect_postbirth",
            "whatsapp_prebirth",
            "whatsapp_postbirth",
        ) or registration.source.authority not in ["hw_partial", "hw_full"]:
            return "POPI Subscription request not created"

        self.log.info("Fetching messageset")
        msgset_short_name = utils.get_messageset_short_name(
            "popi", registration.source.authority, None
        )
        r = utils.get_messageset_schedule_sequence(msgset_short_name, None)
        msgset_id, msgset_schedule, next_sequence_number = r

        self.log.info("Creating subscription request")
        from .models import SubscriptionRequest

        SubscriptionRequest.objects.create(
            identity=registration.registrant_id,
            messageset=msgset_id,
            next_sequence_number=next_sequence_number,
            lang=registration.data["language"],
            schedule=msgset_schedule,
        )
        self.log.info("POPI Subscription request created")
        return "POPI Subscription Request created"

    def create_service_info_subscriptionrequest(self, registration):
        """
        Creates a new subscription request for the service info message set.
        This should only be created for momconnect whatsapp registrations.
        """
        if registration.reg_type not in (
            "whatsapp_prebirth",
            "whatsapp_postbirth",
        ) or registration.source.authority in ["hw_partial", "patient"]:
            return

        self.log.info("Fetching messageset")

        if registration.reg_type == "whatsapp_prebirth":
            weeks = utils.get_pregnancy_week(
                utils.get_today(), registration.data["edd"]
            )
        else:
            weeks = (
                utils.get_baby_age(utils.get_today(), registration.data["baby_dob"])
                + 40
            )
        msgset_short_name = utils.get_messageset_short_name(
            "whatsapp_service_info", registration.source.authority, weeks
        )
        r = utils.get_messageset_schedule_sequence(msgset_short_name, weeks)
        msgset_id, msgset_schedule, next_sequence_number = r

        self.log.info("Creating subscription request")
        from .models import SubscriptionRequest

        SubscriptionRequest.objects.create(
            identity=registration.registrant_id,
            messageset=msgset_id,
            next_sequence_number=next_sequence_number,
            lang=registration.data["language"],
            schedule=msgset_schedule,
        )
        self.log.info("Service Info Subscription request created")

    # Create SubscriptionRequest
    def create_subscriptionrequests(self, registration):
        """ Create SubscriptionRequest(s) based on the
        validated registration.
        """
        self.log.info("Starting subscriptionrequest creation")

        self.log.info("Calculating weeks")
        weeks = 1  # default week number

        # . calculate weeks along
        if registration.reg_type in (
            "momconnect_prebirth",
            "whatsapp_prebirth",
        ) and registration.source.authority not in ["hw_partial", "patient"]:
            weeks = utils.get_pregnancy_week(
                utils.get_today(), registration.data["edd"]
            )

        elif "pmtct_prebirth" in registration.reg_type:
            weeks = utils.get_pregnancy_week(
                utils.get_today(), registration.data["edd"]
            )

        elif "pmtct_postbirth" in registration.reg_type:
            weeks = utils.get_baby_age(utils.get_today(), registration.data["baby_dob"])

        elif (
            registration.reg_type in ("momconnect_postbirth", "whatsapp_postbirth")
            and registration.source.authority == "hw_full"
        ):
            weeks = utils.get_baby_age(utils.get_today(), registration.data["baby_dob"])

        # . determine messageset shortname
        self.log.info("Determining messageset shortname")
        short_name = utils.get_messageset_short_name(
            registration.reg_type, registration.source.authority, weeks
        )

        # . determine sbm details
        self.log.info("Determining SBM details")
        r = utils.get_messageset_schedule_sequence(short_name, weeks)
        msgset_id, msgset_schedule, next_sequence_number = r

        subscription = {
            "identity": registration.registrant_id,
            "messageset": msgset_id,
            "next_sequence_number": next_sequence_number,
            "lang": registration.data["language"],
            "schedule": msgset_schedule,
        }
        self.log.info("Creating SubscriptionRequest object")
        from .models import SubscriptionRequest

        SubscriptionRequest.objects.create(**subscription)
        self.log.info("SubscriptionRequest created")

        return "SubscriptionRequest created"

    # Create ServiceRating Invite
    def create_servicerating_invite(self, registration):
        """ Create a new servicerating invite
        """
        invite_data = {
            "identity": registration.registrant_id
            # could provide "invite" to override servicerating defaults
        }
        self.log.info("Creating ServiceRating invite")
        response = sr_client.create_invite(invite_data)
        self.log.info("Created ServiceRating invite")
        return response

    # Set risk status
    def set_risk_status(self, registration):
        """ Determine the risk status of the mother and save it to her identity
        """
        self.log.info("Calculating risk level")
        risk = get_risk_status(
            registration.reg_type,
            registration.data["mom_dob"],
            registration.data["edd"],
        )
        self.log.info("Reading the identity")
        identity = is_client.get_identity(registration.registrant_id)
        details = identity["details"]

        if "pmtct" in details:
            details["pmtct"]["risk_status"] = risk
        else:
            details["pmtct"] = {"risk_status": risk}

        self.log.info("Saving risk level to the identity")
        is_client.update_identity(registration.registrant_id, {"details": details})

        self.log.info("Identity updated with risk level")
        return risk

    # Run
    def run(self, registration_id, **kwargs):
        """ Sets the registration's validated field to True if
        validation is successful.
        """
        self.log = self.get_logger(**kwargs)
        self.log.info("Looking up the registration")
        from .models import Registration

        registration = Registration.objects.get(id=registration_id)

        if registration.reg_type == "jembi_momconnect":
            # We do this validation in it's own task
            return

        reg_validates = self.validate(registration)
        if reg_validates:
            self.create_subscriptionrequests(registration)
            self.create_popi_subscriptionrequest(registration)
            self.create_service_info_subscriptionrequest(registration)

            # NOTE: disable service rating for now
            # if registration.reg_type == "momconnect_prebirth" and\
            #    registration.source.authority == "hw_full":
            #     self.create_servicerating_invite(registration)

            if "pmtct" in registration.reg_type:
                self.set_risk_status(registration)

            self.log.info("Scheduling registration push to Jembi")
            jembi_task = BasePushRegistrationToJembi.get_jembi_task_for_registration(
                registration
            )
            task = chain(
                jembi_task.si(str(registration.pk)),
                remove_personally_identifiable_fields.si(str(registration.pk)),
            )
            task.delay()

            self.log.info("Task executed successfully")
            return True
        else:
            self.log.info("Task terminated due to validation issues")
            return False


validate_subscribe = ValidateSubscribe()


@app.task()
def remove_personally_identifiable_fields(registration_id):
    """
    Saves the personally identifiable fields to the identity, and then
    removes them from the registration object.
    """
    registration = Registration.objects.get(id=registration_id)

    fields = set(
        (
            "id_type",
            "mom_dob",
            "passport_no",
            "passport_origin",
            "sa_id_no",
            "language",
            "consent",
            "mom_given_name",
            "mom_family_name",
            "mom_email",
        )
    ).intersection(registration.data.keys())
    if fields:
        identity = is_client.get_identity(registration.registrant_id)

        for field in fields:
            #  Language is stored as 'lang_code' in the Identity Store
            if field == "language":
                identity["details"]["lang_code"] = registration.data.pop(field)
                continue
            identity["details"][field] = registration.data.pop(field)

        is_client.update_identity(identity["id"], {"details": identity["details"]})

    msisdn_fields = set(("msisdn_device", "msisdn_registrant")).intersection(
        registration.data.keys()
    )
    for field in msisdn_fields:
        msisdn = registration.data.pop(field)
        identities = is_client.get_identity_by_address("msisdn", msisdn)
        try:
            field_identity = next(identities["results"])
        except StopIteration:
            field_identity = is_client.create_identity(
                {"details": {"addresses": {"msisdn": {msisdn: {}}}}}
            )
        field = field.replace("msisdn", "uuid")
        registration.data[field] = field_identity["id"]

    registration.save()


def add_personally_identifiable_fields(registration):
    """
    Sometimes we might want to rerun the validation and subscription, and for
    that we want to put back any fields that we placed on the identity when
    anonymising the registration.

    This function just adds those fields to the 'registration' object, it
    doesn't save those fields to the database.
    """
    identity = is_client.get_identity(registration.registrant_id)
    if not identity:
        return registration

    fields = (
        set(
            (
                "id_type",
                "mom_dob",
                "passport_no",
                "passport_origin",
                "sa_id_no",
                "lang_code",
                "consent",
                "mom_given_name",
                "mom_family_name",
                "mom_email",
            )
        )
        .intersection(identity["details"].keys())
        .difference(registration.data.keys())
    )
    for field in fields:
        if field == "lang_code":
            registration.data["language"] = identity["details"][field]
            continue
        registration.data[field] = identity["details"][field]

    uuid_fields = set(("uuid_device", "uuid_registrant")).intersection(
        registration.data.keys()
    )
    for field in uuid_fields:
        msisdn = utils.get_identity_msisdn(registration.data[field])
        if msisdn:
            field = field.replace("uuid", "msisdn")
            registration.data[field] = msisdn

    return registration


class ValidateSubscribeJembiAppRegistration(HTTPRetryMixin, ValidateSubscribe):
    """
    Validates and creates subscriptions for registrations coming from the
    Jembi application.
    """

    def is_primary_address(self, addr_type, address, identity):
        """
        Returns whether `address` is the primary address for `identity`

        Arguments:
            addr_type {string} -- The type of address to check for
            address {string} -- The address to check for
            identity {dict} -- The identity that has addresses to check

        Returns:
            A bool which is `True` when the address is the identity's primary
            address.
        """
        return all(
            map(
                lambda addr: address == addr[0] or not addr[1].get("default"),
                identity.get("details", {})
                .get("addresses", {})
                .get(addr_type, {})
                .items(),
            )
        )

    def get_or_update_identity_by_address(self, address):
        """
        Gets the first identity with the given primary address, or if no
        identity exists, creates an identity with the given address

        Arguments:
            address {string} -- The MSISDN to search for

        Returns:
            A dict representing the identity for `address`
        """
        identities = filter(
            partial(self.is_primary_address, "msisdn", address),
            is_client.get_identity_by_address("msisdn", address)["results"],
        )
        try:
            return next(identities)
        except StopIteration:
            identity = {
                "details": {
                    "default_addr_type": "msisdn",
                    "addresses": {"msisdn": {address: {"default": True}}},
                }
            }
            return is_client.create_identity(identity)

    def is_opted_out(self, identity, address):
        """
        Returns whether or not an address on an identity is opted out
        """
        addr_details = identity["details"]["addresses"]["msisdn"][address]
        return "optedout" in addr_details and addr_details["optedout"] is True

    def opt_in(self, identity, address, source):
        """
        Opts in a previously opted out identity
        """
        optin = {
            "identity": identity["id"],
            "address_type": "msisdn",
            "address": address,
            "request_source": source.name,
            "requestor_source_id": source.id,
        }
        return is_client.create_optin(optin)

    def fail_validation(self, registration, reason):
        """
        Validation for the registration has failed
        """
        registration.data["invalid_fields"] = reason
        registration.save()
        return self.send_webhook(registration)

    def fail_error(self, registration, reason):
        """
        Uncaught error that caused the registration to fail
        """
        registration.data["error_data"] = reason
        registration.save()
        return self.send_webhook(registration)

    def registration_success(self, registration):
        """
        Registration has been successfully processed
        """
        return self.send_webhook(registration)

    def send_webhook(self, registration):
        """
        Sends a webhook if one is specified for the given registration
        Also sends the status over websocket
        """
        url = registration.data.get("callback_url", None)
        token = registration.data.get("callback_auth_token", None)

        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer {}".format(token)

        if url is not None:
            http_request_with_retries.delay(
                method="POST", url=url, headers=headers, payload=registration.status
            )

    def is_registered_on_whatsapp(self, address):
        """
        Returns whether or not the number is recognised on wassup
        """
        r = requests.post(
            urljoin(settings.ENGAGE_URL, "v1/contacts"),
            json={"blocking": "wait", "contacts": [address]},
            headers={"Authorization": "Bearer {}".format(settings.ENGAGE_TOKEN)},
        )
        r.raise_for_status()
        data = r.json()
        existing = filter(lambda d: d.get("status", False) == "valid", data["contacts"])
        return any(existing)

    def create_pmtct_registration(self, registration, operator):
        if "whatsapp" in registration.reg_type:
            reg_type = "whatsapp_pmtct_prebirth"
        else:
            reg_type = "pmtct_prebirth"
        data = {
            "language": registration.data["language"],
            "mom_dob": registration.data["mom_dob"],
            "edd": registration.data["edd"],
            "operator_id": operator["id"],
        }
        Registration.objects.create(
            reg_type=reg_type,
            registrant_id=registration.registrant_id,
            source=registration.source,
            created_by=registration.created_by,
            data=data,
        )

    def is_identity_subscribed(self, identity, regex):
        """
        Checks to see if the identity is subscribed to the specified
        messageset. Check is done on the short name of the messageset matching
        the given regular expression
        """
        active_subs = utils.sbm_client.get_subscriptions(
            {"identity": identity["id"], "active": True}
        )["results"]
        messagesets = utils.sbm_client.get_messagesets()["results"]
        messagesets = {ms["id"]: ms["short_name"] for ms in messagesets}
        for sub in active_subs:
            short_name = messagesets[sub["messageset"]]
            if re.search(regex, short_name):
                return True
        return False

    def is_valid_clinic_code(self, code):
        """
        Checks to see if the specified clinic code is recognised or not
        """
        r = requests.get(
            urljoin(settings.JEMBI_BASE_URL, "facilityCheck"),
            {"criteria": "code:{}".format(code)},
            auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
        )
        r.raise_for_status()
        return len(r.json().get("rows", [])) != 0

    def send_welcome_message(
        self, language: str, channel: str, msisdn: str, identity_id: str
    ) -> None:
        """
        Sends the welcome message to the user in the user's language using the
        message sender
        """
        # Transform to django language code
        language = language.lower().replace("_", "-")
        with translation.override(language):
            translation_context = {
                "popi_ussd": settings.POPI_USSD_CODE,
                "optout_ussd": settings.OPTOUT_USSD_CODE,
            }
            if channel == "WHATSAPP":
                text = (
                    translation.ugettext(
                        "Welcome! MomConnect will send helpful WhatsApp msgs. To stop "
                        "dial %(optout_ussd)s (Free). To get msgs via SMS instead, "
                        'reply "SMS" (std rates apply).'
                    )
                    % translation_context
                )
            else:
                text = (
                    translation.ugettext(
                        "Congratulations on your pregnancy! MomConnect will send you "
                        "helpful SMS msgs. To stop dial %(optout_ussd)s, for more dial "
                        "%(popi_ussd)s (Free)."
                    )
                    % translation_context
                )

        utils.ms_client.create_outbound(
            {
                "to_addr": msisdn,
                "to_identity": identity_id,
                "content": text,
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    def run(self, registration_id, **kwargs):
        registration = Registration.objects.get(id=registration_id)
        msisdn_registrant = registration.data["msisdn_registrant"]
        registrant = self.get_or_update_identity_by_address(msisdn_registrant)
        device = self.get_or_update_identity_by_address(
            registration.data["msisdn_device"]
        )
        registration.registrant_id = registrant["id"]

        # Check for existing subscriptions
        if self.is_identity_subscribed(registrant, r"prebirth\.hw_full"):
            self.fail_validation(
                registration,
                {
                    "mom_msisdn": "Number is already subscribed to MomConnect "
                    "messaging"
                },
            )
            return

        # Check for previously opted out
        if self.is_opted_out(registrant, msisdn_registrant):
            if registration.data["mom_opt_in"]:
                self.opt_in(registrant, msisdn_registrant, registration.source)
            else:
                self.fail_validation(
                    registration,
                    {
                        "mom_opt_in": "Mother has previously opted out and has "
                        "not chosen to opt back in again"
                    },
                )
                return

        # Determine WhatsApp vs SMS registration
        registration.data["registered_on_whatsapp"] = self.is_registered_on_whatsapp(
            msisdn_registrant
        )
        if (
            registration.data["mom_whatsapp"]
            and registration.data["registered_on_whatsapp"]
        ):
            registration.reg_type = "whatsapp_prebirth"
        else:
            registration.reg_type = "momconnect_prebirth"

        # Check clinic code
        if not self.is_valid_clinic_code(registration.data["faccode"]):
            self.fail_validation(
                registration, {"clinic_code": "Not a recognised clinic code"}
            )
            return

        registration.validated = True
        registration.save()

        # Create subscriptions
        self.create_subscriptionrequests(registration)
        self.create_popi_subscriptionrequest(registration)
        self.create_service_info_subscriptionrequest(registration)

        # Send welcome message
        self.send_welcome_message(
            language=registration.data["language"],
            channel="WHATSAPP" if "whatsapp" in registration.reg_type else "JUNE_TEXT",
            msisdn=msisdn_registrant,
            identity_id=registration.registrant_id,
        )

        # Push to Jembi and remove personally identifiable information
        jembi_task = BasePushRegistrationToJembi.get_jembi_task_for_registration(
            registration
        )
        task = chain(
            jembi_task.si(str(registration.pk)),
            remove_personally_identifiable_fields.si(str(registration.pk)),
        )
        task.delay()

        # Create PMTCT registration if required
        if registration.data["mom_pmtct"]:
            self.create_pmtct_registration(registration, device)

        # Send success webhook
        self.registration_success(registration)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super(ValidateSubscribeJembiAppRegistration, self).on_failure(
            exc, task_id, args, kwargs, einfo
        )
        # Send failure webhook
        registration_id = kwargs.get("registration_id", None) or args[0]
        registration = Registration.objects.get(id=registration_id)
        self.fail_error(
            registration,
            {
                "type": einfo.type.__name__,
                "message": str(exc),
                "traceback": einfo.traceback,
            },
        )


validate_subscribe_jembi_app_registration = ValidateSubscribeJembiAppRegistration()


class BasePushRegistrationToJembi(object):
    """
    Base class that contains helper functions for pushing registration data
    to Jembi.
    """

    name = "ndoh_hub.registrations.tasks.base_push_registration_to_jembi"
    log = get_task_logger(__name__)

    def get_patient_id(
        self, id_type, id_no=None, passport_origin=None, mom_msisdn=None
    ):
        if id_type == "sa_id":
            return id_no + "^^^ZAF^NI"
        elif id_type == "passport":
            return id_no + "^^^" + passport_origin.upper() + "^PPN"
        elif mom_msisdn:
            return mom_msisdn.replace("+", "") + "^^^ZAF^TEL"

    def get_dob(self, mom_dob):
        if mom_dob is not None:
            return mom_dob.strftime("%Y%m%d")
        else:
            return None

    def get_today(self):
        return datetime.today()

    def get_timestamp(self, registration):
        return registration.created_at.strftime("%Y%m%d%H%M%S")

    @staticmethod
    def get_jembi_task_for_registration(registration):
        """
        NOTE:   this is a convenience method for getting the relevant
                Jembi task to fire for a registration.
        """
        if "nurseconnect" in registration.reg_type:
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
        source_name = source.name.upper()
        if source_name.startswith("EXTERNAL CHW"):
            # catch all external chw sources
            return "chw"
        elif source_name.startswith("EXTERNAL CLINIC"):
            # catch all external clinic sources
            return "clinic"
        else:
            return {
                "PUBLIC USSD APP": "personal",
                "OPTOUT USSD APP": "optout",
                "CLINIC USSD APP": "clinic",
                "CHW USSD APP": "chw",
                "NURSE USSD APP": "nurse",
                "PMTCT USSD APP": "pmtct",
                "PUBLIC WHATSAPP APP": "personal",
                "CLINIC WHATSAPP APP": "clinic",
            }.get(source_name)

    def run(self, registration_id, **kwargs):
        from .models import Registration

        registration = Registration.objects.get(pk=registration_id)
        authority = self.get_authority_from_source(registration.source)
        if authority is None:
            self.log.error(
                "Unable to establish authority for source %s. Skipping."
                % (registration.source)
            )
            return

        json_doc = self.build_jembi_json(registration)
        request_to_jembi_api(self.URL, json_doc)


class PushRegistrationToJembi(BasePushRegistrationToJembi, Task):
    """ Task to push registration data to Jembi
    """

    name = "ndoh_hub.registrations.tasks.push_registration_to_jembi"
    log = get_task_logger(__name__)
    URL = urljoin(settings.JEMBI_BASE_URL, "subscription")

    def get_subscription_type(self, authority):
        authority_map = {
            "personal": 1,
            "chw": 2,
            "clinic": 3,
            "optout": 4,
            # NOTE: these are other valid values recognised by Jembi but
            #       currently not used by us.
            # 'babyloss': 5,
            # 'servicerating': 6,
            # 'helpdesk': 7,
            "pmtct": 9,
        }
        return authority_map[authority]

    def get_software_type(self, registration):
        """ Get the software type (swt) code Jembi expects """
        if registration.data.get("swt", None):
            return registration.data.get("swt")
        if "whatsapp" in registration.reg_type:
            registration.data["swt"] = 7  # USSD4WHATSAPP
            registration.save()
            return 7
        return 1  # Default 1

    def transform_language_code(self, lang):
        return {
            "zul_ZA": "zu",
            "xho_ZA": "xh",
            "afr_ZA": "af",
            "eng_ZA": "en",
            "nso_ZA": "nso",
            "tsn_ZA": "tn",
            "sot_ZA": "st",
            "tso_ZA": "ts",
            "ssw_ZA": "ss",
            "ven_ZA": "ve",
            "nbl_ZA": "nr",
        }[lang]

    def build_jembi_json(self, registration):
        """ Compile json to be sent to Jembi. """
        self.log.info("Compiling Jembi Json data for PushRegistrationToJembi")
        authority = self.get_authority_from_source(registration.source)

        id_msisdn = None
        if not registration.data.get("msisdn_registrant"):
            id_msisdn = utils.get_identity_msisdn(registration.registrant_id)

        json_template = {
            "mha": registration.data.get("mha", 1),
            "swt": self.get_software_type(registration),
            "dmsisdn": registration.data.get("msisdn_device"),
            "cmsisdn": registration.data.get("msisdn_registrant", id_msisdn),
            "id": self.get_patient_id(
                registration.data.get("id_type"),
                (
                    registration.data.get("sa_id_no")
                    if registration.data.get("id_type") == "sa_id"
                    else registration.data.get("passport_no")
                ),
                # passport_origin may be None if sa_id is used
                registration.data.get("passport_origin"),
                registration.data.get("msisdn_registrant", id_msisdn),
            ),
            "type": self.get_subscription_type(authority),
            "lang": self.transform_language_code(registration.data["language"]),
            "encdate": registration.data.get(
                "encdate", self.get_timestamp(registration)
            ),
            "faccode": registration.data.get("faccode"),
            "dob": (
                self.get_dob(
                    datetime.strptime(registration.data["mom_dob"], "%Y-%m-%d")
                )
                if registration.data.get("mom_dob")
                else None
            ),
            "eid": str(registration.id),
        }

        # Self registrations on all lines should use cmsisdn as dmsisdn too
        if registration.data.get("msisdn_device") is None:
            json_template["dmsisdn"] = registration.data.get(
                "msisdn_registrant", id_msisdn
            )

        if authority == "clinic":
            json_template["edd"] = datetime.strptime(
                registration.data["edd"], "%Y-%m-%d"
            ).strftime("%Y%m%d")

        return json_template


push_registration_to_jembi = PushRegistrationToJembi()


class PushPmtctRegistrationToJembi(PushRegistrationToJembi, Task):
    """ Task to push PMTCT registration data to Jembi
    """

    name = "ndoh_hub.registrations.tasks.push_pmtct_registration_to_jembi"
    URL = urljoin(settings.JEMBI_BASE_URL, "pmtctSubscription")

    def build_jembi_json(self, registration):
        json_template = super(PushPmtctRegistrationToJembi, self).build_jembi_json(
            registration
        )

        json_template["risk_status"] = get_risk_status(
            registration.reg_type,
            registration.data["mom_dob"],
            registration.data["edd"],
        )

        if not json_template.get("faccode"):
            related_reg = (
                Registration.objects.filter(
                    validated=True,
                    registrant_id=registration.registrant_id,
                    data__has_key="faccode",
                )
                .exclude(
                    reg_type__in=(
                        "whatsapp_pmtct_prebirth",
                        "pmtct_prebirth",
                        "whatsapp_pmtct_postbirth",
                        "pmtct_postbirth",
                    )
                )
                .order_by("-created_at")
                .first()
            )

            if related_reg:
                json_template["faccode"] = related_reg.data["faccode"]

        return json_template


push_pmtct_registration_to_jembi = PushPmtctRegistrationToJembi()


class PushNurseRegistrationToJembi(BasePushRegistrationToJembi, Task):
    name = "ndoh_hub.registrations.tasks.push_nurse_registration_to_jembi"
    log = get_task_logger(__name__)
    URL = urljoin(settings.JEMBI_BASE_URL, "nc/subscription")

    def get_persal(self, identity):
        details = identity["details"]
        return details.get("nurseconnect", {}).get("persal_no")

    def get_sanc(self, identity):
        details = identity["details"]
        return details.get("nurseconnect", {}).get("sanc_reg_no")

    def get_software_type(self, registration):
        """ Get the software type (swt) code Jembi expects """
        if registration.data.get("swt", None):
            return registration.data.get("swt")
        if "whatsapp" in registration.reg_type:
            registration.data["swt"] = 7  # USSD4WHATSAPP
            registration.save(update_fields=("data",))
            return 7
        return 3  # Default 3

    def build_jembi_json(self, registration):
        """
        Compiles and returns a dictionary representing the JSON that should
        be sent to Jembi for the given registration.
        """
        self.log.info("Compiling Jembi Json data for PushNurseRegistrationToJembi")
        identity = is_client.get_identity(registration.registrant_id)
        json_template = {
            "mha": 1,
            "swt": self.get_software_type(registration),
            "type": 7,
            "dmsisdn": registration.data["msisdn_device"],
            "cmsisdn": registration.data["msisdn_registrant"],
            # NOTE: this likely needs to be updated to reflect a change
            #       in msisdn as `rmsisdn` stands for replacement msisdn
            "rmsisdn": None,
            "faccode": registration.data["faccode"],
            "id": self.get_patient_id(
                registration.data.get("id_type"),
                (
                    registration.data.get("sa_id_no")
                    if registration.data.get("id_type") == "sa_id"
                    else registration.data.get("passport_no")
                ),
                # passport_origin may be None if sa_id is used
                registration.data.get("passport_origin"),
                registration.data["msisdn_registrant"],
            ),
            "dob": (
                self.get_dob(
                    datetime.strptime(registration.data["mom_dob"], "%Y-%m-%d")
                )
                if registration.data.get("mom_db")
                else None
            ),
            "persal": self.get_persal(identity),
            "sanc": self.get_sanc(identity),
            "encdate": self.get_timestamp(registration),
            "eid": str(registration.id),
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
                "Content-Type": "application/json",
                "Authorization": "Token %s" % settings.HOOK_AUTH_TOKEN,
            },
        )


def deliver_hook_wrapper(target, payload, instance, hook):
    if instance is not None:
        if isinstance(instance.id, uuid.UUID):
            instance_id = str(instance.id)
        else:
            instance_id = instance.id
    else:
        instance_id = None
    kwargs = dict(
        target=target, payload=payload, instance_id=instance_id, hook_id=hook.id
    )
    DeliverHook.apply_async(kwargs=kwargs)


class HTTPRequestWithRetries(HTTPRetryMixin, Task):
    def run(self, method, url, headers, payload):
        r = requests.request(method, url, headers=headers, json=payload)
        r.raise_for_status()
        return r.text


http_request_with_retries = HTTPRequestWithRetries()


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_whatsapp_contact(msisdn):
    """
    Fetches the whatsapp contact ID from the API, and stores it in the database.

    Args:
        msisdn (str): The MSISDN to perform the lookup for.
    """
    try:
        whatsapp_id = utils.wab_client.get_address(msisdn)
    except AddressException:
        whatsapp_id = ""
    WhatsAppContact.objects.update_or_create(
        msisdn=msisdn, defaults={"whatsapp_id": whatsapp_id}
    )


@app.task(
    autoretry_for=(RequestException, HTTPServiceError, SoftTimeLimitExceeded),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_or_create_identity_from_msisdn(context, field):
    """
    Fetches the identity from the identity store using the MSISDN in the context from
    `field` adds it to the context as `{field}_identity`. Creates the identity if it
    doesn't exist.

    Args:
        context (dict): The context to find the msisdn and add the ID in
        field (str): The field in the context that contains the MSISDN
    """
    msisdn = phonenumbers.parse(context[field], "ZA")
    msisdn = phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
    try:
        identity = next(
            utils.is_client.get_identity_by_address("msisdn", msisdn)["results"]
        )
    except StopIteration:
        identity = utils.is_client.create_identity(
            {
                "details": {
                    "default_addr_type": "msisdn",
                    "addresses": {"msisdn": {msisdn: {"default": True}}},
                }
            }
        )
    context["{}_identity".format(field)] = identity
    return context


@app.task(
    autoretry_for=(RequestException, HTTPServiceError, SoftTimeLimitExceeded),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def update_identity_from_rapidpro_clinic_registration(context):
    """
    Updates the identity's details from the registration details
    """
    identity = context["mom_msisdn_identity"]
    identity["details"]["lang_code"] = context["mom_lang"]
    identity["details"]["consent"] = True
    identity["details"]["last_mc_reg_on"] = "clinic"

    if context["mom_id_type"] == "sa_id":
        identity["details"]["sa_id_no"] = context["mom_sa_id_no"]
        identity["details"]["mom_dob"] = datetime.strptime(
            context["mom_sa_id_no"][:6], "%y%m%d"
        ).strftime("%Y-%m-%d")
    elif context["mom_id_type"] == "passport":
        identity["details"]["passport_no"] = context["mom_passport_no"]
        identity["details"]["passport_origin"] = context["mom_passport_origin"]
    else:  # mom_id_type == none
        identity["details"]["mom_dob"] = context["mom_dob"]

    if context["registration_type"] == "prebirth":
        identity["details"]["last_edd"] = context["mom_edd"]
    else:  # registration_type == postbirth
        identity["details"]["last_baby_dob"] = context["baby_dob"]

    context["mom_msisdn_identity"] = utils.is_client.update_identity(
        identity["id"], {"details": identity["details"]}
    )
    return context


@app.task(
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def _create_rapidpro_clinic_registration(context):
    """
    Creates the registration from the registration details
    """
    user = User.objects.get(id=context["user_id"])
    source = Source.objects.get(user=user)

    reg_type = {
        ("prebirth", "WhatsApp"): "whatsapp_prebirth",
        ("prebirth", "SMS"): "momconnect_prebirth",
        ("postbirth", "WhatsApp"): "whatsapp_postbirth",
        ("postbirth", "SMS"): "momconnect_postbirth",
    }.get((context["registration_type"], context["channel"]))

    data = {
        "operator_id": context["device_msisdn_identity"]["id"],
        "msisdn_registrant": context["mom_msisdn"],
        "msisdn_device": context["device_msisdn"],
        "id_type": context["mom_id_type"],
        "language": context["mom_lang"],
        "faccode": context["clinic_code"],
        "consent": True,
        "mha": 6,
    }

    if data["id_type"] == "sa_id":
        data["sa_id_no"] = context["mom_sa_id_no"]
        data["mom_dob"] = datetime.strptime(
            context["mom_sa_id_no"][:6], "%y%m%d"
        ).strftime("%Y-%m-%d")
    elif data["id_type"] == "passport":
        data["passport_no"] = context["mom_passport_no"]
        data["passport_origin"] = context["mom_passport_origin"]
    else:  # id_type = None
        data["mom_dob"] = context["mom_dob"]

    if context["registration_type"] == "prebirth":
        data["edd"] = context["mom_edd"]
    else:  # registration_type = postbirth
        data["baby_dob"] = context["baby_dob"]

    Registration.objects.create(
        reg_type=reg_type,
        registrant_id=context["mom_msisdn_identity"]["id"],
        source=source,
        created_by=user,
        updated_by=user,
        data=data,
    )


create_rapidpro_clinic_registration = (
    get_or_create_identity_from_msisdn.s("mom_msisdn")
    | update_identity_from_rapidpro_clinic_registration.s()
    | get_or_create_identity_from_msisdn.s("device_msisdn")
    | _create_rapidpro_clinic_registration.s()
)


@app.task(
    autoretry_for=(RequestException, HTTPServiceError, SoftTimeLimitExceeded),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def update_identity_from_rapidpro_public_registration(context):
    """
    Updates the identity's details from the registration details
    """
    identity = context["mom_msisdn_identity"]
    identity["details"]["lang_code"] = context["mom_lang"]
    identity["details"]["consent"] = True
    identity["details"]["last_mc_reg_on"] = "public"

    context["mom_msisdn_identity"] = utils.is_client.update_identity(
        identity["id"], {"details": identity["details"]}
    )
    return context


@app.task(
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def _create_rapidpro_public_registration(context):
    user = User.objects.get(id=context["user_id"])
    source = Source.objects.get(user=user)

    data = {
        "operator_id": context["mom_msisdn_identity"]["id"],
        "msisdn_registrant": context["mom_msisdn"],
        "msisdn_device": context["mom_msisdn"],
        "language": context["mom_lang"],
        "consent": True,
        "registered_on_whatsapp": True,
        "mha": 6,
    }

    Registration.objects.create(
        reg_type="whatsapp_prebirth",
        registrant_id=context["mom_msisdn_identity"]["id"],
        source=source,
        created_by=user,
        updated_by=user,
        data=data,
    )


create_rapidpro_public_registration = (
    get_or_create_identity_from_msisdn.s("mom_msisdn")
    | update_identity_from_rapidpro_public_registration.s()
    | _create_rapidpro_public_registration.s()
)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def request_to_jembi_api(url, json_doc):
    r = requests.post(
        url=url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(json_doc),
        auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
        verify=False,
    )
    r.raise_for_status()
    return r.raise_for_status()
