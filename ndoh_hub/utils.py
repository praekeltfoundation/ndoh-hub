from __future__ import division

import datetime
import responses

from django.conf import settings
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient  # noqa


sbm_client = StageBasedMessagingApiClient(
    api_url=settings.STAGE_BASED_MESSAGING_URL,
    auth_token=settings.STAGE_BASED_MESSAGING_TOKEN
)


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


# def patch_identity(identity, data):
#     """ Patches the given identity with the data provided
#     """
#     url = "%s/%s/%s/" % (settings.IDENTITY_STORE_URL, "identities", identity)
#     data = data
#     headers = {
#         'Authorization': 'Token %s' % settings.IDENTITY_STORE_TOKEN,
#         'Content-Type': 'application/json'
#     }
#     r = requests.patch(url, data=json.dumps(data), headers=headers)
#     r.raise_for_status()
#     return r.json()


# def get_messageset(messageset_id):
#     url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL, "messageset",
#                          messageset_id)
#     headers = {
#         'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
#         'Content-Type': 'application/json'
#     }
#     r = requests.get(url, headers=headers)
#     r.raise_for_status()
#     return r.json()


# def get_schedule(schedule_id):
#     url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL,
#                          "schedule", schedule_id)
#     headers = {
#         'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
#         'Content-Type': 'application/json'
#     }
#     r = requests.get(url, headers=headers)
#     r.raise_for_status()
#     return r.json()


# def get_subscriptions(params):
#     url = "%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL, "subscriptions")
#     headers = {
#         'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
#         'Content-Type': 'application/json'
#     }
#     r = requests.get(url, params=params, headers=headers)
#     r.raise_for_status()
#     return r.json()


# def patch_subscription(subscription_id, data):
#     """ Patches the given subscription with the data provided
#     """
#     url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL,
#                          "subscriptions", subscription_id)
#     data = data
#     headers = {
#         'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
#         'Content-Type': 'application/json'
#     }
#     r = requests.patch(url, data=json.dumps(data), headers=headers)
#     r.raise_for_status()
#     return r.json()


def get_messageset_short_name(reg_type, authority, weeks):
    batch_number = 1  # default batch_number

    if "prebirth" in reg_type:
        if 30 <= weeks <= 34:
            batch_number = 2
        elif weeks >= 35:
            batch_number = 3

    if "postbirth" in reg_type:
        if weeks > 1:
            batch_number = 2

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

    return (messageset["id"], messageset["default_schedule"],
            next_sequence_number)


# Mocks used in testing
def mock_get_identity_by_id(identity_id):
    identity = {
        "id": identity_id,
        "version": 1,
        "details": {
            "foo": "bar"
        },
        "communicate_through": None,
        "operator": None,
        "created_at": "2016-03-31T09:28:29.506591Z",
        "created_by": None,
        "updated_at": "2016-08-17T09:44:31.812532Z",
        "updated_by": 1
    }

    responses.add(
        responses.GET,
        'http://is/api/v1/identities/%s/' % identity_id,
        json=identity,
        status=200, content_type='application/json'
    )


def mock_patch_identity(identity_id):
    patched_identity = {
        "id": identity_id,
        "version": 1,
        "details": {
            "foo": "bar",
            "risk": "high"
        },
        "communicate_through": None,
        "operator": None,
        "created_at": "2016-03-31T09:28:29.506591Z",
        "created_by": None,
        "updated_at": "2016-08-17T09:44:31.812532Z",
        "updated_by": 1
    }

    responses.add(
        responses.PATCH,
        'http://is/api/v1/identities/%s/' % identity_id,
        json=patched_identity,
        status=200, content_type='application/json'
    )


def mock_get_messageset_by_shortname(short_name):
    messageset_id = {
        "pmtct_prebirth.patient.1": 11,
        "pmtct_prebirth.patient.2": 12,
        "pmtct_prebirth.patient.3": 13,
        "pmtct_postbirth.patient.1": 14,
        "pmtct_postbirth.patient.2": 15,
        "momconnect_prebirth.hw_full.1": 21,
        "momconnect_prebirth.hw_full.2": 22,
        "momconnect_prebirth.hw_full.3": 23,
        "momconnect_prebirth.hw_full.4": 24,
        "momconnect_prebirth.hw_full.5": 25,
        "momconnect_prebirth.hw_full.6": 26,
        "momconnect_postbirth.hw_full.1": 31,
        "momconnect_postbirth.hw_full.2": 32,
        "momconnect_prebirth.patient.1": 41,
        "momconnect_prebirth.hw_partial.1": 42,
        "loss_miscarriage.patient.1": 51,
        "loss_stillbirth.patient.1": 52,
        "loss_babydeath.patient.1": 53,
        "nurseconnect.hw_full.1": 61
    }[short_name]

    default_schedule = {
        "pmtct_prebirth.patient.1": 111,
        "pmtct_prebirth.patient.2": 112,
        "pmtct_prebirth.patient.3": 113,
        "pmtct_postbirth.patient.1": 114,
        "pmtct_postbirth.patient.2": 115,
        "momconnect_prebirth.hw_full.1": 121,
        "momconnect_prebirth.hw_full.2": 122,
        "momconnect_prebirth.hw_full.3": 123,
        "momconnect_prebirth.hw_full.4": 124,
        "momconnect_prebirth.hw_full.5": 125,
        "momconnect_prebirth.hw_full.6": 126,
        "momconnect_postbirth.hw_full.1": 131,
        "momconnect_postbirth.hw_full.2": 132,
        "momconnect_prebirth.patient.1": 141,
        "momconnect_prebirth.hw_partial.1": 142,
        "loss_miscarriage.patient.1": 151,
        "loss_stillbirth.patient.1": 152,
        "loss_babydeath.patient.1": 153,
        "nurseconnect.hw_full.1": 161
    }[short_name]

    responses.add(
        responses.GET,
        'http://sbm/api/v1/messageset/?short_name=%s' % short_name,
        json={
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{
                "id": messageset_id,
                "short_name": short_name,
                "default_schedule": default_schedule
            }]
        },
        status=200, content_type='application/json',
        match_querystring=True
    )
    return default_schedule


def mock_get_messageset(messageset_id):
    short_name = {
        11: "pmtct_prebirth.patient.1",
        12: "pmtct_prebirth.patient.2",
        13: "pmtct_prebirth.patient.3",
        14: "pmtct_postbirth.patient.1",
        15: "pmtct_postbirth.patient.2",
        21: "momconnect_prebirth.hw_full.1",
        22: "momconnect_prebirth.hw_full.2",
        23: "momconnect_prebirth.hw_full.3",
        24: "momconnect_prebirth.hw_full.4",
        25: "momconnect_prebirth.hw_full.5",
        26: "momconnect_prebirth.hw_full.6",
        31: "momconnect_postbirth.hw_full.1",
        32: "momconnect_postbirth.hw_full.2",
        41: "momconnect_prebirth.patient.1",
        42: "momconnect_prebirth.hw_partial.1",
        51: "loss_miscarriage.patient.1",
        52: "loss_stillbirth.patient.1",
        53: "loss_babydeath.patient.1",
        61: "nurseconnect.hw_full.1"
    }[messageset_id]

    default_schedule = {
        "pmtct_prebirth.patient.1": 111,
        "pmtct_prebirth.patient.2": 112,
        "pmtct_prebirth.patient.3": 113,
        "pmtct_postbirth.patient.1": 114,
        "pmtct_postbirth.patient.2": 115,
        "momconnect_prebirth.hw_full.1": 121,
        "momconnect_prebirth.hw_full.2": 122,
        "momconnect_prebirth.hw_full.3": 123,
        "momconnect_prebirth.hw_full.4": 124,
        "momconnect_prebirth.hw_full.5": 125,
        "momconnect_prebirth.hw_full.6": 126,
        "momconnect_postbirth.hw_full.1": 131,
        "momconnect_postbirth.hw_full.2": 132,
        "momconnect_prebirth.patient.1": 141,
        "momconnect_prebirth.hw_partial.1": 142,
        "loss_miscarriage.patient.1": 151,
        "loss_stillbirth.patient.1": 152,
        "loss_babydeath.patient.1": 153,
        "nurseconnect.hw_full.1": 161
    }[short_name]

    responses.add(
        responses.GET,
        'http://sbm/api/v1/messageset/%s/' % messageset_id,
        json={
            'id': messageset_id,
            'short_name': short_name,
            'notes': None,
            'next_set': 10,
            'default_schedule': default_schedule,
            'content_type': 'text',
            'created_at': "2016-06-22T06:13:29.693272Z",
            'updated_at': "2016-06-22T06:13:29.693272Z"
        }
    )


def mock_get_schedule(schedule_id):
    day_of_week = {
        111: "1",
        112: "1,4",
        113: "1,3,5",
        114: "1,4",
        115: "1",
        121: "1,4",
        122: "1,3,5",
        123: "1,3,5",
        124: "1,2,3,4",
        125: "1,2,3,4,5",
        126: "1,2,3,4,5,6,7",
        131: "1,4",
        132: "1",
        141: "1,4",
        142: "1,4",
        151: "1,4",
        152: "1,4",
        153: "1,4",
        161: "1,3,5"
    }[schedule_id]

    responses.add(
        responses.GET,
        'http://sbm/api/v1/schedule/%s/' % schedule_id,
        json={"id": schedule_id, "day_of_week": day_of_week},
        status=200, content_type='application/json',
    )
