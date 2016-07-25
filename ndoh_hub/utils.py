import datetime
import requests
import json

from django.conf import settings


def get_today():
    return datetime.datetime.today()


def get_pregnancy_week(today, edd):
    """ Calculate how far along the mother's prenancy is in weeks. """
    due_date = datetime.datetime.strptime(edd, "%Y-%m-%d")
    time_diff = due_date - today
    time_diff_weeks = time_diff.days / 7
    preg_weeks = 40 - time_diff_weeks
    # You can't be less than two week pregnant
    if preg_weeks <= 1:
        preg_weeks = 2  # changed from JS's 'false' to achieve same result
    return preg_weeks


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


def get_messageset(short_name):
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


def get_subscriptions(identity):
    """ Gets the first active subscription found for an identity
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

    short_name = "%s.%s.%s" % (reg_type, authority, batch_number)

    return short_name


def get_messageset_schedule_sequence(short_name, weeks):
    # get messageset
    messageset = get_messageset(short_name)

    # calculate next_sequence_number
    next_sequence_number = 1  # to be expanded with momconnect migration

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
