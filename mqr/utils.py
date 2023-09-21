from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from django.conf import settings

from ndoh_hub.utils import get_today
from registrations.models import ClinicCode


def get_week(subscription_type, edd_or_dob_date):
    if subscription_type == "pre":
        if edd_or_dob_date < get_today():
            return 40 + (abs(get_today() - edd_or_dob_date).days // 7)
        else:
            return 40 - (abs(get_today() - edd_or_dob_date).days // 7)
    else:
        return abs(get_today() - edd_or_dob_date).days // 7


def get_tag(arm, subscription_type, edd_or_dob_date, tag_extra=None):
    week = get_week(subscription_type, edd_or_dob_date)

    label = f"{arm}_week_{subscription_type}{week}"
    if tag_extra:
        label = f"{label}_{tag_extra}"
    return label.lower()


def get_message(page_id, tracking_data):
    tracking_data["whatsapp"] = "True"
    url = urljoin(settings.MQR_CONTENTREPO_URL, f"/api/v2/pages/{page_id}/")
    response = requests.get(url, params=tracking_data)
    response.raise_for_status()

    page = response.json()
    message = page["body"]["text"]["value"]["message"]

    if "whatsapp_template" in page.get("tags", []):
        page_title = page["title"]
        latest_revision_id = page["body"]["revision"]
        template_name = f"{page_title}_{latest_revision_id}"
        return True, "{{1}}" in message, message, template_name

    return False, False, message, None


def get_message_details(tag, tracking_data, mom_name=None):
    url = urljoin(settings.MQR_CONTENTREPO_URL, f"api/v2/pages?tag={tag}")
    response = requests.get(url)
    response.raise_for_status()

    if len(response.json()["results"]) == 1:
        page_id = response.json()["results"][0]["id"]
        is_template, has_parameters, message, template_name = get_message(
            page_id, tracking_data
        )

        if mom_name:
            message = message.replace("{{1}}", mom_name)

        return {
            "is_template": is_template,
            "has_parameters": has_parameters,
            "message": message,
            "template_name": template_name,
        }
    if len(response.json()["results"]) == 0:
        return {"warning": "no message found"}
    elif len(response.json()["results"]) > 1:
        return {"error": "multiple message found"}


def get_next_message(
    edd_or_dob_date,
    subscription_type,
    arm,
    tag_extra,
    mom_name,
    tracking_data,
):
    tag = get_tag(arm, subscription_type, edd_or_dob_date, tag_extra)

    response = get_message_details(tag, tracking_data, mom_name)

    response["next_send_date"] = get_next_send_date()
    response["tag"] = tag

    return response


def get_midweek_arm_message(last_tag, mom_name, tracking_data):
    tag = f"{last_tag}_mid"
    response = get_message_details(tag, tracking_data, mom_name)
    response["tag"] = tag
    return response


def get_next_arm_message(last_tag, sequence, mom_name, tracking_data):
    tag = f"{last_tag}_{sequence}"
    response = get_message_details(tag, tracking_data, mom_name)

    next_sequence = chr(ord(sequence) + 1)
    next_tag = f"{last_tag}_{next_sequence}"
    url = urljoin(settings.MQR_CONTENTREPO_URL, f"api/v2/pages?tag={next_tag}")
    contentrepo_response = requests.get(url)
    contentrepo_response.raise_for_status()

    add_prompt = True

    if "*yes*" in response["message"].split("\n")[-1].lower():
        add_prompt = False

    if len(contentrepo_response.json()["results"]) == 1:
        prompt_message = "To get another helpful message tomorrow, reply *YES*."
        response["has_next_message"] = True
    else:
        prompt_message = "-----\nReply:\n*MENU* for the main menu 📌"
        response["has_next_message"] = False

    if add_prompt:
        base_message = response["message"]
        response["message"] = f"{base_message}\n\n{prompt_message}"

    return response


def get_faq_message(tag, faq_number, viewed, tracking_data):
    bcm = "_bcm_" in tag
    tag = tag.replace("_bcm_", "_")

    faq_tag = f"{tag}_faq{faq_number}"
    response = get_message_details(faq_tag, tracking_data)

    viewed.append(faq_tag)

    faq_menu, faq_numbers = get_faq_menu(tag, viewed, bcm)

    response["faq_menu"] = faq_menu
    response["faq_numbers"] = faq_numbers
    response["viewed"] = viewed

    return response


def get_faq_menu(tag, viewed, bcm, menu_offset=0):
    viewed_filter = ",".join(viewed)
    url = urljoin(
        settings.MQR_CONTENTREPO_URL, f"/faqmenu?viewed={viewed_filter}&tag={tag}"
    )
    response = requests.get(url)
    response.raise_for_status()

    pages = response.json()

    faq_numbers = []
    menu = []
    for i, page in enumerate(pages):
        order = str(page["order"])
        title = page["title"].replace("*", "")

        faq_numbers.append(order)
        menu.append(f"*{i+1+menu_offset}* - {title}")

    if bcm:
        option = len(menu) + 1 + menu_offset
        menu.append(f"*{option}* - *FIND* more topics 🔎")

    return "\n".join(menu), ",".join(faq_numbers)


def get_next_send_date():
    return get_today() + timedelta(weeks=1)


def get_first_send_date(edd_or_dob_date):
    full_weeks = (get_today() - edd_or_dob_date).days // 7 + 1
    return edd_or_dob_date + timedelta(weeks=full_weeks)


def is_study_active_for_weeks_pregnant(estimated_delivery_date):
    study_start_date = datetime.strptime(
        settings.MQR_STUDY_START_DATE, "%Y-%m-%d"
    ).date()

    weeks_pregnant = get_week("pre", estimated_delivery_date)
    study_active_weeks = (get_today() - study_start_date).days // 7

    if study_active_weeks <= settings.MQR_WEEK_LIMIT_OFFSET:
        return True

    study_min_weeks = study_active_weeks + 15 - settings.MQR_WEEK_LIMIT_OFFSET

    return weeks_pregnant >= study_min_weeks


def get_facility_province(facility_code):
    try:
        clinic_code = ClinicCode.objects.get(code=facility_code)
    except ClinicCode.DoesNotExist:
        clinic_code = None

    return clinic_code


def get_weeks_pregnant(registration_date, estimated_date):
    full_term_weeks = 40

    # Get remaining weeks
    remaining_weeks = (estimated_date - registration_date).days // 7

    weeks_pregnant = full_term_weeks - remaining_weeks

    if 16 <= weeks_pregnant <= 20:
        return "16-20"
    elif 21 <= weeks_pregnant <= 25:
        return "21-25"
    elif 26 <= weeks_pregnant <= 30:
        return "26-30"
    else:
        return None


def get_age_bucket(mom_age):
    # Get age range
    if 18 <= mom_age <= 30:
        return "18-30"
    elif mom_age >= 31:
        return "31+"
    else:
        return None
