import json
import uuid
from datetime import datetime

import requests
from requests.exceptions import HTTPError

from django.conf import settings
from celery import chain
from celery.task import Task
from celery.utils.log import get_task_logger
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.service_rating import ServiceRatingApiClient

from ndoh_hub import utils
from ndoh_hub.celery import app
from .models import Registration


is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL,
    auth_token=settings.IDENTITY_STORE_TOKEN
)

sr_client = ServiceRatingApiClient(
    api_url=settings.SERVICE_RATING_URL,
    auth_token=settings.SERVICE_RATING_TOKEN
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
        elif not utils.is_valid_edd(registration.data["edd"]):
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

        if "pmtct_prebirth" in registration.reg_type:
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_edd(data_fields, registration)
            validation_errors += self.check_operator_id(
                data_fields, registration)

        elif "pmtct_postbirth" in registration.reg_type:
            validation_errors += self.check_lang(data_fields, registration)
            validation_errors += self.check_mom_dob(data_fields, registration)
            validation_errors += self.check_baby_dob(data_fields, registration)
            validation_errors += self.check_operator_id(
                data_fields, registration)

        elif 'nurseconnect' in registration.reg_type:
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

        elif registration.reg_type in [
                "momconnect_prebirth", "whatsapp_prebirth"]:
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

    def create_popi_subscriptionrequest(self, registration):
        """
        Creates a new subscription request for the POPI message set. This
        message set tells the user how to access the POPI required services.
        This should only be sent for Clinic or CHW registrations.
        """
        if ('prebirth' not in registration.reg_type or
           registration.source.authority not in ['hw_partial', 'hw_full']):
            return "POPI Subscription request not created"

        self.l.info("Fetching messageset")
        msgset_short_name = utils.get_messageset_short_name(
            'popi', registration.source.authority, None)
        msgset_id, msgset_schedule, next_sequence_number =\
            utils.get_messageset_schedule_sequence(msgset_short_name, None)

        self.l.info("Creating subscription request")
        from .models import SubscriptionRequest
        SubscriptionRequest.objects.create(
            identity=registration.registrant_id,
            messageset=msgset_id,
            next_sequence_number=next_sequence_number,
            lang=registration.data['language'],
            schedule=msgset_schedule,
        )
        self.l.info("POPI Subscription request created")
        return "POPI Subscription Request created"

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

        elif "pmtct_prebirth" in registration.reg_type:
            weeks = utils.get_pregnancy_week(utils.get_today(),
                                             registration.data["edd"])

        elif "pmtct_postbirth" in registration.reg_type:
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
            self.create_popi_subscriptionrequest(registration)

            # NOTE: disable service rating for now
            # if registration.reg_type == "momconnect_prebirth" and\
            #    registration.source.authority == "hw_full":
            #     self.create_servicerating_invite(registration)

            if "pmtct" in registration.reg_type:
                self.set_risk_status(registration)

            self.l.info("Scheduling registration push to Jembi")
            jembi_task = BasePushRegistrationToJembi.\
                get_jembi_task_for_registration(registration)
            task = chain(
                jembi_task.si(str(registration.pk)),
                remove_personally_identifiable_fields.si(str(registration.pk))
            )
            task.delay()

            self.l.info("Task executed successfully")
            return True
        else:
            self.l.info("Task terminated due to validation issues")
            return False


validate_subscribe = ValidateSubscribe()


@app.task()
def remove_personally_identifiable_fields(registration_id):
    """
    Saves the personally identifiable fields to the identity, and then
    removes them from the registration object.
    """
    registration = Registration.objects.get(id=registration_id)

    fields = set((
        'id_type', 'mom_dob', 'passport_no', 'passport_origin', 'sa_id_no',
        'language', 'consent')).intersection(registration.data.keys())
    if fields:
        identity = is_client.get_identity(registration.registrant_id)

        for field in fields:
            #  Language is stored as 'lang_code' in the Identity Store
            if field == 'language':
                identity['details']['lang_code'] = registration.data.pop(field)
                continue
            identity['details'][field] = registration.data.pop(field)

        is_client.update_identity(
            identity['id'], {'details': identity['details']})

    msisdn_fields = set((
        'msisdn_device', 'msisdn_registrant')
        ).intersection(registration.data.keys())
    for field in msisdn_fields:
        msisdn = registration.data.pop(field)
        identities = is_client.get_identity_by_address('msisdn', msisdn)
        try:
            field_identity = next(identities['results'])
        except StopIteration:
            field_identity = is_client.create_identity({
                'details': {
                    'addresses': {
                        'msisdn': {msisdn: {}},
                    },
                },
            })
        field = field.replace('msisdn', 'uuid')
        registration.data[field] = field_identity['id']

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

    fields = set((
        'id_type', 'mom_dob', 'passport_no', 'passport_origin', 'sa_id_no',
        'lang_code', 'consent'))\
        .intersection(identity['details'].keys())\
        .difference(registration.data.keys())
    for field in fields:
        if field == 'lang_code':
            registration.data['language'] = identity['details'][field]
            continue
        registration.data[field] = identity['details'][field]

    uuid_fields = set((
        'uuid_device', 'uuid_registrant')
        ).intersection(registration.data.keys())
    for field in uuid_fields:
        msisdn = utils.get_identity_msisdn(registration.data[field])
        if msisdn:
            field = field.replace('uuid', 'msisdn')
            registration.data[field] = msisdn

    return registration


class BasePushRegistrationToJembi(object):
    """
    Base class that contains helper functions for pushing registration data
    to Jembi.
    """
    name = "ndoh_hub.registrations.tasks.base_push_registration_to_jembi"
    l = get_task_logger(__name__)

    def get_patient_id(self, id_type, id_no=None, passport_origin=None,
                       mom_msisdn=None):
        if id_type == 'sa_id':
            return id_no + "^^^ZAF^NI"
        elif id_type == 'passport':
            return id_no + '^^^' + passport_origin.upper() + '^PPN'
        elif mom_msisdn:
            return mom_msisdn.replace('+', '') + '^^^ZAF^TEL'

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
        if 'nurseconnect' in registration.reg_type:
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
        if source_name.startswith('EXTERNAL CHW'):
            # catch all external chw sources
            return 'chw'
        elif source_name.startswith('EXTERNAL CLINIC'):
            # catch all external clinic sources
            return 'clinic'
        else:
            return {
                'PUBLIC USSD APP': 'personal',
                'OPTOUT USSD APP': 'optout',
                'CLINIC USSD APP': 'clinic',
                'CHW USSD APP': 'chw',
                'NURSE USSD APP': 'nurse',
                'PMTCT USSD APP': 'pmtct',
            }.get(source_name)

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

    def get_software_type(self, registration):
        """ Get the software type (swt) code Jembi expects """
        if registration.data.get('swt', None):
            return registration.data.get('swt')
        if "whatsapp" in registration.reg_type:
            registration.data['swt'] = 7  # USSD4WHATSAPP
            registration.save()
            return 7
        return 1  # Default 1

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

        id_msisdn = None
        if not registration.data.get('msisdn_registrant'):
            id_msisdn = utils.get_identity_msisdn(registration.registrant_id)

        json_template = {
            "mha": registration.data.get('mha', 1),
            "swt": self.get_software_type(registration),
            "dmsisdn": registration.data.get('msisdn_device'),
            "cmsisdn": registration.data.get('msisdn_registrant', id_msisdn),
            "id": self.get_patient_id(
                registration.data.get('id_type'),
                (registration.data.get('sa_id_no')
                 if registration.data.get('id_type') == 'sa_id'
                 else registration.data.get('passport_no')),
                # passport_origin may be None if sa_id is used
                registration.data.get('passport_origin'),
                registration.data.get('msisdn_registrant', id_msisdn)),
            "type": self.get_subscription_type(authority),
            "lang": self.transform_language_code(
                registration.data['language']),
            "encdate": registration.data.get('encdate',
                                             self.get_timestamp(registration)),
            "faccode": registration.data.get('faccode'),
            "dob": (self.get_dob(
                datetime.strptime(registration.data['mom_dob'], '%Y-%m-%d'))
                    if registration.data.get('mom_dob')
                    else None)
        }

        # Self registrations on all lines should use cmsisdn as dmsisdn too
        if registration.data.get('msisdn_device') is None:
            json_template["dmsisdn"] = registration.data.get(
                'msisdn_registrant', id_msisdn)

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

    def build_jembi_json(self, registration):
        json_template = super(PushPmtctRegistrationToJembi, self).\
            build_jembi_json(registration)

        json_template["risk_status"] = get_risk_status(
            registration.reg_type,
            registration.data["mom_dob"],
            registration.data["edd"])

        if not json_template.get('faccode'):
            related_reg = Registration.objects.filter(
                    validated=True,
                    registrant_id=registration.registrant_id,
                    data__has_key='faccode').\
                exclude(reg_type__in=(
                    "whatsapp_pmtct_prebirth", "pmtct_prebirth",
                    "whatsapp_pmtct_postbirth", "pmtct_postbirth")).\
                order_by('-created_at').first()

            if related_reg:
                json_template['faccode'] = related_reg.data['faccode']

        return json_template

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
            "encdate": self.get_timestamp(registration),
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
