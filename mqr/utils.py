from datetime import timedelta
from urllib.parse import urljoin

import requests
from django.conf import settings

from ndoh_hub.utils import get_today


def get_tag(arm, subscription_type, edd_or_dob_date, sequence=None):
    week = abs(get_today() - edd_or_dob_date).days // 7

    label = f"{arm}_week_{subscription_type}{week}"
    if sequence:
        label = f"{label}_{sequence}"
    return label.lower()


def get_message(page_id):
    url = urljoin(
        settings.MQR_CONTENTREPO_URL, f"/api/v2/pages/{page_id}/?whatsapp=True"
    )
    response = requests.get(url)
    response.raise_for_status()

    page = response.json()
    message = page["body"]["text"]["value"]["message"]

    if page.get("is_whatsapp_template"):
        return True, "{{1}}" in message, page["title"]

    return False, False, message


def get_message_details(tag, mom_name=None):
    url = urljoin(settings.MQR_CONTENTREPO_URL, f"api/v2/pages?tag={tag}")
    response = requests.get(url)
    response.raise_for_status()

    if len(response.json()["results"]) == 1:
        page_id = response.json()["results"][0]["id"]
        is_template, has_parameters, message = get_message(page_id)

        if not is_template and mom_name:
            message = message.replace("{{1}}", mom_name)

        return {
            "is_template": is_template,
            "has_parameters": has_parameters,
            "message": message,
        }
    if len(response.json()["results"]) == 0:
        return {"error": "no message found"}
    elif len(response.json()["results"]) > 1:
        return {"error": "multiple message found"}


def get_next_message(edd_or_dob_date, subscription_type, arm, sequence, mom_name):
    tag = get_tag(arm, subscription_type, edd_or_dob_date, sequence)

    response = get_message_details(tag, mom_name)

    response["next_send_date"] = get_next_send_date()
    response["tag"] = tag

    return response


def get_next_send_date():
    # TODO: maybe this should be smarter
    # calculate date based on edd_or_dob and next week, incase message failed?
    return get_today() + timedelta(weeks=1)
