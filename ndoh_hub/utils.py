from __future__ import division

import datetime
import requests
import json
import responses

from django.conf import settings


def get_today():
    return datetime.datetime.today()


def get_mom_age(today, mom_dob):
    """ Calculate the mother's age in years """
    birth_date = datetime.datetime.strptime(mom_dob, "%Y-%m-%d")
    time_diff = today - birth_date
    # timedelta limitation - approximate year to 365 days
    mom_age = int(round(time_diff.days // 365))
    return mom_age


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


def get_identity(identity):
    url = "%s/%s/%s/" % (settings.IDENTITY_STORE_URL, "identities", identity)
    headers = {'Authorization': 'Token %s' % settings.IDENTITY_STORE_TOKEN,
               'Content-Type': 'application/json'}
    r = requests.get(url, headers=headers)
    return r.json()


def get_identity_address(identity):
    url = "%s/%s/%s/addresses/msisdn" % (settings.IDENTITY_STORE_URL,
                                         "identities", identity)
    params = {"default": True}
    headers = {'Authorization': 'Token %s' % (
        settings.IDENTITY_STORE_TOKEN, ),
        'Content-Type': 'application/json'}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    result = r.json()
    if len(result["results"]) > 0:
        return result["results"][0]
    else:
        return None


def patch_identity(identity, data):
    """ Patches the given identity with the data provided
    """
    url = "%s/%s/%s/" % (settings.IDENTITY_STORE_URL, "identities", identity)
    data = data
    headers = {
        'Authorization': 'Token %s' % settings.IDENTITY_STORE_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.patch(url, data=json.dumps(data), headers=headers)
    r.raise_for_status()
    return r.json()


def get_messageset_by_id(messageset_id):
    url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL, "messageset",
                         messageset_id)
    headers = {
        'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_messageset_by_shortname(short_name):
    url = "%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL, "messageset")
    params = {'short_name': short_name}
    headers = {
        'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()["results"][0]  # messagesets should be unique, return 1st


def get_schedule(schedule_id):
    url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL,
                         "schedule", schedule_id)
    headers = {
        'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_active_subscriptions(identity):
    """ Gets the active subscriptions for an identity
    """
    url = "%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL, "subscriptions")
    params = {'id': identity, 'active': True}
    headers = {
        'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()["results"]


def patch_subscription(subscription, data):
    """ Patches the given subscription with the data provided
    """
    url = "%s/%s/%s/" % (settings.STAGE_BASED_MESSAGING_URL,
                         "subscriptions", subscription["id"])
    data = data
    headers = {
        'Authorization': 'Token %s' % settings.STAGE_BASED_MESSAGING_TOKEN,
        'Content-Type': 'application/json'
    }
    r = requests.patch(url, data=json.dumps(data), headers=headers)
    r.raise_for_status()
    return r.json()


def deactivate_subscription(subscription):
    """ Sets a subscription deactive via a Patch request
    """
    return patch_subscription(subscription, {"active": False})


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
    messageset = get_messageset_by_shortname(short_name)

    if "prebirth" in short_name:
        # get schedule
        schedule = get_schedule(messageset["default_schedule"])
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


def post_message(payload):
    result = requests.post(
        url="%s/outbound/" % settings.MESSAGE_SENDER_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Token %s' % settings.MESSAGE_SENDER_TOKEN
        }
    )
    result.raise_for_status()
    return result.json()


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
    }[short_name]

    default_schedule = {
        "pmtct_prebirth.patient.1": 111,
        "pmtct_prebirth.patient.2": 112,
        "pmtct_prebirth.patient.3": 113,
        "pmtct_postbirth.patient.1": 114,
        "pmtct_postbirth.patient.2": 115,
        "momconnect_prebirth.hw_full.1": 121
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


def mock_get_messageset_by_id(messageset_id):
    short_name = {
        11: "pmtct_prebirth.patient.1",
        12: "pmtct_prebirth.patient.2",
        13: "pmtct_prebirth.patient.3",
        14: "pmtct_postbirth.patient.1",
        15: "pmtct_postbirth.patient.2",
        21: "momconnect_prebirth.hw_full.1",
    }[messageset_id]

    default_schedule = {
        "pmtct_prebirth.patient.1": 111,
        "pmtct_prebirth.patient.2": 112,
        "pmtct_prebirth.patient.3": 113,
        "pmtct_postbirth.patient.1": 114,
        "pmtct_postbirth.patient.2": 115,
        "momconnect_prebirth.hw_full.1": 121,
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
        112: "1,3",
        113: "1,3,5",
        114: "1,4",
        115: "1",
        121: "1,4"
    }[schedule_id]

    responses.add(
        responses.GET,
        'http://sbm/api/v1/schedule/%s/' % schedule_id,
        json={"id": schedule_id, "day_of_week": day_of_week},
        status=200, content_type='application/json',
    )
