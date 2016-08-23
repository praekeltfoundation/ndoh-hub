from __future__ import division

import datetime

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
