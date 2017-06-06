from __future__ import division
from __future__ import absolute_import

import datetime

from celery.task import Task
from django.conf import settings
from go_http.metrics import MetricsApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient  # noqa


sbm_client = StageBasedMessagingApiClient(
    api_url=settings.STAGE_BASED_MESSAGING_URL,
    auth_token=settings.STAGE_BASED_MESSAGING_TOKEN
)


def is_valid_uuid(id):
    return len(id) == 36 and id[14] == '4' and id[19] in ['a', 'b', '8', '9']


def is_valid_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
        return True
    except:
        return False


def is_valid_lang(lang):
    return lang in [
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


# TODO 15: Improve validation functions
def is_valid_msisdn(msisdn):
    """ A very basic msisdn validation check """
    return msisdn[0] == '+' and len(msisdn) == 12


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
    valid_origins = ["na", "bw", "mz", "sz", "ls", "cu", "zw", "mw", "ng",
                     "cd", "so", "other"]
    return passport_origin in valid_origins


def get_today():
    return datetime.datetime.today()


def get_mom_age(today, mom_dob):
    """ Calculate the mother's age in years """
    born = datetime.datetime.strptime(mom_dob, "%Y-%m-%d")
    return today.year - born.year - (
        (today.month, today.day) < (born.month, born.day))


def get_pregnancy_week(today, edd):
    """ Calculate how far along the mother's prenancy is in weeks. """
    due_date = datetime.datetime.strptime(edd, "%Y-%m-%d")
    time_diff = due_date - today
    time_diff_weeks = int(round(time_diff.days // 7))
    preg_weeks = 40 - time_diff_weeks
    # You can't be less than two week pregnant
    if preg_weeks <= 1:
        preg_weeks = 2  # changed from JS's 'false' to achieve same result
    return preg_weeks


def get_baby_age(today, baby_dob):
    """ Calculate the baby's age in weeks """
    birth_date = datetime.datetime.strptime(baby_dob, "%Y-%m-%d")
    time_diff = today - birth_date
    baby_age_weeks = int(round(time_diff.days // 7))
    return baby_age_weeks


def get_messageset_short_name(reg_type, authority, weeks):
    batch_number = 1  # default batch_number

    if reg_type == "pmtct_prebirth":
        if 30 <= weeks <= 34:
            batch_number = 2
        elif weeks >= 35:
            batch_number = 3

    elif reg_type == "pmtct_postbirth":
        if weeks > 1:
            batch_number = 2

    elif reg_type == "momconnect_prebirth" and authority == "hw_full":
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

    short_name = "%s.%s.%s" % (reg_type, authority, batch_number)

    return short_name


def get_messageset_schedule_sequence(short_name, weeks):
    # get messageset
    messageset = sbm_client.get_messagesets(
        {"short_name": short_name})["results"][0]

    if "prebirth" in short_name:
        # get schedule
        schedule = sbm_client.get_schedule(messageset["default_schedule"])
        # get schedule days of week: comma-seperated str e.g. '1,3' for Mon&Wed
        days_of_week = schedule["day_of_week"]
        # determine how many times a week messages are sent e.g. 2 for '1,3'
        msgs_per_week = len(days_of_week.split(','))

    next_sequence_number = 1  # default to 1

    # calculate next_sequence_number
    if short_name == 'pmtct_prebirth.patient.1':
        if weeks >= 7:
            next_sequence_number = (weeks - 6) * msgs_per_week

    elif short_name == 'pmtct_prebirth.patient.2':
        if weeks >= 31:
            next_sequence_number = (weeks - 30) * msgs_per_week

    elif short_name == 'pmtct_prebirth.patient.3':
        if 36 <= weeks <= 41:
            next_sequence_number = (weeks - 35) * msgs_per_week
        if weeks >= 42:
            next_sequence_number = 20  # last message in set

    elif short_name == 'pmtct_postbirth.patient.1':
        if weeks == 1:
            next_sequence_number = 3

    elif short_name == 'pmtct_postbirth.patient.2':
        if weeks <= 50:
            next_sequence_number = weeks - 1
        else:
            next_sequence_number = 50  # last message in set

    # nurseconnect always starts at 1

    elif short_name == 'momconnect_prebirth.hw_full.1':
        if weeks >= 5:
            next_sequence_number = ((weeks - 4) * msgs_per_week) - 1

    elif short_name == 'momconnect_prebirth.hw_full.2':
        if weeks >= 32:
            next_sequence_number = ((weeks - 30) * msgs_per_week) - 2

    # other momconnect_prebirth sets start at 1

    # loss subscriptions always start at 1

    return (messageset["id"], messageset["default_schedule"],
            next_sequence_number)


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


def get_metric_client(session=None):
    return MetricsApiClient(
        auth_token=settings.METRICS_AUTH_TOKEN,
        api_url=settings.METRICS_URL,
        session=session)


class FireMetric(Task):

    """ Fires a metric using the MetricsApiClient
    """
    name = "ndoh_hub.tasks.fire_metric"

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
