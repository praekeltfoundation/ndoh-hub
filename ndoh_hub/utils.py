from __future__ import absolute_import, division

import datetime
import json

import six
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.message_sender import MessageSenderApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient

from registrations.models import PositionTracker

ID_TYPES = ["sa_id", "passport", "none"]
PASSPORT_ORIGINS = [
    "na",
    "bw",
    "mz",
    "sz",
    "ls",
    "cu",
    "zw",
    "mw",
    "ng",
    "cd",
    "so",
    "other",
]
LANGUAGES = [
    "zul_ZA",  # isiZulu
    "xho_ZA",  # isiXhosa
    "afr_ZA",  # Afrikaans
    "eng_ZA",  # English
    "nso_ZA",  # Sesotho sa Leboa / Pedi
    "tsn_ZA",  # Setswana
    "sot_ZA",  # Sesotho
    "tso_ZA",  # Xitsonga
    "ssw_ZA",  # siSwati
    "ven_ZA",  # Tshivenda
    "nbl_ZA",  # isiNdebele
]

sbm_client = StageBasedMessagingApiClient(
    api_url=settings.STAGE_BASED_MESSAGING_URL,
    auth_token=settings.STAGE_BASED_MESSAGING_TOKEN,
)

is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL, auth_token=settings.IDENTITY_STORE_TOKEN
)

ms_client = MessageSenderApiClient(
    api_url=settings.MESSAGE_SENDER_URL, auth_token=settings.MESSAGE_SENDER_TOKEN
)


def get_identity_msisdn(registrant_id):
    """
    Given an identity UUID, returns the msisdn for the identity. Takes into
    account default addresses, opted out addresses, and missing identities
    or addresses. Returns None when it cannot find an MSISDN address.
    """
    identity = is_client.get_identity(registrant_id)
    if not identity:
        return

    msisdns = identity["details"].get("addresses", {}).get("msisdn", {})

    identity_msisdn = None
    for msisdn, details in msisdns.items():
        if "default" in details and details["default"]:
            return msisdn
        if not ("optedout" in details and details["optedout"]):
            identity_msisdn = msisdn
    return identity_msisdn


def is_valid_uuid(id):
    return len(id) == 36 and id[14] == "4" and id[19] in ["a", "b", "8", "9"]


def is_valid_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
        return True
    except Exception:
        return False


def is_valid_edd_date(edd):
    """
    Checks given Estimated Due Date is in the future but not more than
    9 months away
    """
    return edd > get_today() and edd < get_today() + datetime.timedelta(weeks=43)


def is_valid_edd(date):
    """
    Checks given Estimated Due Date is in the future but not more than
    9 months away
    """
    if is_valid_date(date):
        edd = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return is_valid_edd_date(edd)
    return False


def is_valid_lang(lang):
    return lang in LANGUAGES


# TODO 15: Improve validation functions
def is_valid_msisdn(msisdn):
    """ A very basic msisdn validation check """
    return msisdn[0] == "+" and len(msisdn) == 12


def is_valid_faccode(faccode):
    """ A very basic faccode validation check """
    return len(faccode) >= 1


def is_valid_sanc_no(sanc_no):
    """ A very basic sanc_no validation check """
    return len(sanc_no) >= 1


def is_valid_persal_no(persal_no):
    """ A very basic persal_no validation check """
    return len(persal_no) >= 1


def is_valid_sa_id_no(sa_id_no):
    """ A very basic sa_id_no validation check """
    return len(sa_id_no) == 13


def is_valid_passport_no(passport_no):
    """ A very basic passport_no validation check """
    return len(passport_no) >= 1


def is_valid_passport_origin(passport_origin):
    """ A passport_origin validation check """
    return passport_origin in PASSPORT_ORIGINS


def is_valid_id_type(id_type):
    """ A ID type check """
    return id_type in ID_TYPES


def get_today():
    return datetime.date.today()


def get_mom_age(today, mom_dob):
    """ Calculate the mother's age in years """
    born = datetime.datetime.strptime(mom_dob, "%Y-%m-%d")
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def get_pregnancy_week(today, edd):
    """ Calculate how far along the mother's prenancy is in weeks. """
    due_date = datetime.datetime.strptime(edd, "%Y-%m-%d").date()
    time_diff = due_date - today
    time_diff_weeks = int(round(time_diff.days // 7))
    preg_weeks = 40 - time_diff_weeks
    # You can't be less than two week pregnant
    if preg_weeks <= 1:
        preg_weeks = 2  # changed from JS's 'false' to achieve same result
    return preg_weeks


def get_baby_age(today, baby_dob):
    """ Calculate the baby's age in weeks """
    birth_date = datetime.datetime.strptime(baby_dob, "%Y-%m-%d").date()
    time_diff = today - birth_date
    baby_age_weeks = int(round(time_diff.days // 7))
    return baby_age_weeks


def get_messageset_short_name(reg_type, authority, weeks):
    batch_number = 1  # default batch_number

    if reg_type == "whatsapp_prebirth":
        reg_type = "whatsapp_momconnect_prebirth"

    if "pmtct_prebirth" in reg_type:
        if 30 <= weeks <= 34:
            batch_number = 2
        elif weeks >= 35:
            batch_number = 3

    elif "pmtct_postbirth" in reg_type:
        if weeks > 1:
            batch_number = 2

    elif "momconnect_prebirth" in reg_type and authority == "hw_full":
        if weeks <= 30:
            batch_number = 1
        elif weeks <= 35:
            batch_number = 2
        elif weeks <= 36:
            batch_number = 3
        elif weeks <= 37:
            batch_number = 4
        elif weeks <= 38:
            batch_number = 5
        else:
            batch_number = 6

    # If the RTHB messaging is enabled, all nurseconnect subscriptions should
    # start on the RTHB messageset
    elif settings.NURSECONNECT_RTHB and "nurseconnect" in reg_type:
        reg_type += "_rthb"

    short_name = "%s.%s.%s" % (reg_type, authority, batch_number)

    return short_name


def get_messageset_schedule_sequence(short_name, weeks):
    # get messageset
    messageset = next(sbm_client.get_messagesets({"short_name": short_name})["results"])

    if "prebirth" in short_name:
        # get schedule
        schedule = sbm_client.get_schedule(messageset["default_schedule"])
        # get schedule days of week: comma-seperated str e.g. '1,3' for Mon&Wed
        days_of_week = schedule["day_of_week"]
        # determine how many times a week messages are sent e.g. 2 for '1,3'
        msgs_per_week = len(days_of_week.split(","))

    next_sequence_number = 1  # default to 1

    # calculate next_sequence_number
    if "pmtct_prebirth.patient.1" in short_name:
        if weeks >= 7:
            next_sequence_number = (weeks - 6) * msgs_per_week

    elif "pmtct_prebirth.patient.2" in short_name:
        if weeks >= 31:
            next_sequence_number = (weeks - 30) * msgs_per_week

    elif "pmtct_prebirth.patient.3" in short_name:
        if 36 <= weeks <= 41:
            next_sequence_number = (weeks - 35) * msgs_per_week
        if weeks >= 42:
            next_sequence_number = 20  # last message in set

    elif "pmtct_postbirth.patient.1" in short_name:
        if weeks == 1:
            next_sequence_number = 3

    elif "pmtct_postbirth.patient.2" in short_name:
        if weeks <= 50:
            next_sequence_number = weeks - 1
        else:
            next_sequence_number = 50  # last message in set

    # nurseconnect always starts at 1

    elif "momconnect_prebirth.hw_full.1" in short_name:
        if weeks >= 5:
            next_sequence_number = ((weeks - 4) * msgs_per_week) - 1

    elif "momconnect_prebirth.hw_full.2" in short_name:
        if weeks >= 32:
            next_sequence_number = ((weeks - 30) * msgs_per_week) - 2

    # WhatsApp service info messages depend on months pregnant
    elif "whatsapp_service_info.hw_full.1" in short_name:
        if weeks >= 5:
            next_sequence_number = ((weeks - 4) // 4) + 1

    # other momconnect_prebirth sets start at 1

    # loss subscriptions always start at 1

    # RTHB NurseConnect subscriptions are tracked by the position tracker
    if "nurseconnect_rthb" in short_name:
        next_sequence_number = PositionTracker.objects.get(
            label="nurseconnect_rthb"
        ).position

    return (messageset["id"], messageset["default_schedule"], next_sequence_number)


def append_or_create(dictionary, field, value):
    """
    If 'field' exists in 'dictionary', it appends 'value' to the existing
    list, else it creates the field with a list that comprises of 'value'
    """
    if field in dictionary:
        dictionary[field].append(value)
    else:
        dictionary[field] = [value]


def get_available_metrics():
    available_metrics = []
    available_metrics.extend(settings.METRICS_REALTIME)
    available_metrics.extend(settings.METRICS_SCHEDULED)
    return available_metrics


def json_decode(data):
    """
    Decodes the given JSON as primitives
    """
    if isinstance(data, six.binary_type):
        data = data.decode("utf-8")

    return json.loads(data)


class TokenAuthQueryString(TokenAuthentication):
    """
    Look for the token in the querystring parameter "token"
    """

    def authenticate(self, request):
        token = request.query_params.get("token", None)
        if token is not None:
            return self.authenticate_credentials(token)
        return None


# Since WhatsApp doesn't support most of South Africa's official languages, we create
# a mapping to languages that we don't use for missing languages
WHATSAPP_LANGUAGE_MAP = {
    "zul_ZA": "uz",
    "xho_ZA": "th",
    "afr_ZA": "af",
    "eng_ZA": "en",
    "nso_ZA": "sl",
    "tsn_ZA": "bn",
    "sot_ZA": "ta",
    "tso_ZA": "sv",
    "ssw_ZA": "sw",
    "ven_ZA": "vi",
    "nbl_ZA": "nb",
}
