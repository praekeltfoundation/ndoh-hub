from __future__ import absolute_import, division

from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings
from django.urls import reverse
from temba_client.v2 import TembaClient

rapidpro = None
if settings.RAPIDPRO_URL and settings.RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)


def assessmentkeywords():
    keywords = ["0", "ACCEPT", "CONTINUE", "BACK", "MENU"]
    return keywords


def build_rp_request(body):
    # The cardType value is used to build the request to ADA
    if "cardType" in body.keys():
        cardType = body["cardType"]
    else:
        cardType = ""
    if "step" in body.keys():
        step = body["step"]
    else:
        step = ""
    if "value" in body.keys():
        value = body["value"]
    else:
        value = ""

    if cardType != "" and value.upper() != "BACK":
        if cardType == "TEXT":
            payload = {"step": step}
        elif cardType == "INPUT":
            payload = {"step": step, "value": value}
        elif cardType == "CHOICE":
            payload = {"step": step, "optionId": int(value) - 1}
    elif cardType == "" and step == 0:
        payload = {"step": 0}
    elif value.upper() == "BACK":
        payload = {"step": step}
    else:
        payload = {}

    return payload


def post_to_ada(body, path, contact_uuid):
    head = get_header(contact_uuid)
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    response = requests.post(path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def post_to_ada_start_assessment(body, contact_uuid):
    head = get_header(contact_uuid)
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, "/assessments")
    response = requests.post(path, body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def format_message(body):
    description = body["description"]["en-GB"]
    title = body["title"]["en-GB"]
    back = (
        "Reply *back* to go to the previous question or *menu* to end the assessment."
    )
    explain = "Reply *EXPLAIN* to see what this means."
    textcontinue = "Reply *0* to continue."
    cardType = body["cardType"]
    if "explanations" in body.keys():
        explanations = body["explanations"][0]["text"]["en-GB"]
    else:
        explanations = ""
    if "options" in body.keys() and cardType != "CHOICE":
        optionId = body["options"][0]["optionId"]
    else:
        optionId = None
    path = body["_links"]["next"]["href"]
    if "step" in body.keys():
        step = body["step"]
    else:
        step = ""
    if cardType == "CHOICE":
        option = body["options"][0]["text"]["en-GB"]
        optionslist = []
        index = 0
        length = len(body["options"])
        while index < length:
            optionslist.append(body["options"][index]["text"]["en-GB"])
            index += 1
        choiceContext = optionslist[:]
        for i in range(len(optionslist)):
            optionslist[i] = f"{i+1}. {optionslist[i]}"

        choices = "\n".join(optionslist)
        extra_message = (
            f"Choose the option that matches your answer. Eg, *1* for *{option}*"
        )
        if explanations != "":
            message = (
                f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}\n\n{explain}"
            )
        else:
            message = f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}"
        body = {}
        body["choices"] = length
        body["choiceContext"] = choiceContext
    elif cardType == "TEXT":
        message = f"{description}\n\n{textcontinue}\n\n{back}"
        body = {}
    else:
        placeholder = body["cardAttributes"]["placeholder"]["en-GB"]
        message = f"{description}\n\n_{placeholder}_\n\n{back}"
        format = body["cardAttributes"]["format"]
        body = {}
        body["choices"] = None
        body["formatType"] = format

    body["message"] = message
    body["explanations"] = explanations
    body["step"] = step
    body["optionId"] = optionId
    body["path"] = path
    body["cardType"] = cardType
    body["title"] = title
    body["description"] = description
    return body


def get_endpoint(payload):
    value = payload["value"]
    value = value.upper()
    if value != "":
        if value == "BACK":
            url = reverse("ada-previous-dialog")
        elif value == "MENU":
            url = reverse("ada-abort")
        else:
            url = reverse("ada-next-dialog")
    elif value == "":
        url = reverse("ada-start-assessment")
    return url


def encodeurl(payload, url):
    qs = "?" + urlencode(payload, safe="")
    reverse_url = url + qs
    return reverse_url


def get_path(body):
    if "path" in body.keys():
        path = body["path"]
    else:
        path = body["_links"]["startAssessment"]["href"]
    return path


def get_step(body):
    step = body["step"]
    return step


def pdf_ready(data):
    try:
        data["_links"]["report"]["href"]
        return True
    except KeyError:
        return False


def pdf_endpoint(data):
    report_path = data["_links"]["report"]["href"]
    qs = "?report_path=" + report_path
    url = reverse("ada-reports")
    reverse_url = url + qs
    return reverse_url


# This returns the report of the assessment
def get_report(path, contact_uuid):
    head = get_header_pdf(contact_uuid)
    payload = {}
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    response = requests.get(path, json=payload, headers=head)
    response.raise_for_status()
    return response.content


def upload_turn_media(media, content_type="application/pdf"):
    headers = {
        "Authorization": "Bearer {}".format(settings.ADA_TURN_TOKEN),
        "Content-Type": content_type,
    }
    response = requests.post(
        urljoin(settings.ADA_TURN_URL, "v1/media"), headers=headers, data=media
    )
    response.raise_for_status()
    return response.json()["media"][0]["id"]


# Go back to previous question
def previous_question(body, path, contact_uuid):
    head = get_header(contact_uuid)
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    path = path.replace("/next", "/previous")
    response = requests.post(path, json=body, headers=head)
    response = response.json()
    return response


# Abort assessment
def abort_assessment(body):
    contact_uuid = body["contact_uuid"]
    head = get_header(contact_uuid)
    path = body["path"]
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    path = path.replace("dialog/next", "/abort")
    payload = {}
    response = requests.put(path, json=payload, headers=head).json()
    response.raise_for_status()
    return response


def get_header(contact_uuid):
    head = {
        "x-ada-clientId": settings.X_ADA_CLIENTID,
        "x-ada-userId": contact_uuid,
        "Accept-Language": "en-GB",
        "Content-Type": "application/json",
    }
    return head


def get_header_pdf(contact_uuid):
    head = {
        "x-ada-clientId": settings.X_ADA_CLIENTID,
        "x-ada-userId": contact_uuid,
        "Accept-Language": "en-GB",
        "Content-Type": "application/pdf",
    }
    return head
