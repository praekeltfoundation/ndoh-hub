from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from django.conf import settings

from ndoh_hub.utils import get_today
from registrations.models import ClinicCode


def get_tag(arm, subscription_type, edd_or_dob_date, sequence=None):
    week = abs(get_today() - edd_or_dob_date).days // 7

    label = f"{arm}_week_{subscription_type}{week}"
    if sequence:
        label = f"{label}_{sequence}"
    return label


def get_message(page_id):
    url = urljoin(
        settings.MQR_CONTENTREPO_URL, f"/api/v2/pages/{page_id}/?whatsapp=True"
    )
    response = requests.get(url)
    response.raise_for_status()

    page = response.json()

    if page.get("is_whatsapp_template"):
        return True, page["title"]

    return False, page["body"]["text"]["value"]["message"]


def get_message_details(tag):
    url = urljoin(settings.MQR_CONTENTREPO_URL, f"api/v2/pages?tag={tag}")
    response = requests.get(url)
    response.raise_for_status()

    if len(response.json()["results"]) == 1:
        page_id = response.json()["results"][0]["id"]
        is_template, message = get_message(page_id)

        return {"is_template": is_template, "message": message}
    if len(response.json()["results"]) == 0:
        return {"error": "no message found"}
    elif len(response.json()["results"]) > 1:
        return {"error": "multiple message found"}


def get_next_send_date():
    # TODO: maybe this should be smarter
    # calculate date based on edd_or_dob and next week, incase message failed?
    return datetime.today().date() + timedelta(weeks=1)


def get_facility_province(facility_code):
    try:
        clinic_code = ClinicCode.objects.get(code=facility_code)
    except ClinicCode.DoesNotExist:
        clinic_code = None

    return clinic_code


def get_weeks_pregnant(edd):
    full_term_weeks = 40
    estimated_date = edd

    if isinstance(edd, str):
        # convert to date
        estimated_date = datetime.strptime(edd, "%Y-%m-%d").date()
    elif isinstance(edd, datetime):
        estimated_date = edd.date()

    # Get remaining weeks
    remaining_weeks = (estimated_date - get_today()).days // 7

    weeks_pregnant = full_term_weeks - remaining_weeks

    if 16 <= weeks_pregnant <= 20:
        return "16-20"
    elif 21 <= weeks_pregnant <= 25:
        return "21-25"
    elif 26 <= weeks_pregnant <= 30:
        return "26-30"
    else:
        return None


def get_age_bucket(age):
    mom_age = int(age)

    # Get age range
    if 18 <= mom_age <= 30:
        return "18-30"
    elif mom_age >= 31:
        return "31+"
    else:
        return None
