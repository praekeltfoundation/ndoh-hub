from __future__ import absolute_import, division

import json
import urllib.parse
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


def inputTypeKeywords():
    keywords = ["BACK", "MENU"]
    return keywords


def choiceTypeKeywords():
    keywords = ["BACK", "MENU"]
    return keywords


def get_max(payload):
    try:
        max = payload["cardAttributes"]["maximum"]["value"]
        error = payload["cardAttributes"]["maximum"]["message"]
        return max, error
    except KeyError:
        return None


def get_min(payload):
    try:
        min = payload["cardAttributes"]["minimum"]["value"]
        error = payload["cardAttributes"]["minimum"]["message"]
        type = "number"
        return min, error, type
    except KeyError:
        pass
    try:
        pattern = payload["cardAttributes"]["pattern"]["value"]
        error = payload["cardAttributes"]["pattern"]["message"]
        type = "regex"
        return pattern, error, type
    except KeyError:
        return None


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
    try:
        body["_links"]["next"]["href"]
        next_question = True
    except KeyError:
        next_question = False
    try:
        pdf_media_id = body["pdf_media_id"]
    except KeyError:
        pdf_media_id = ""
    description = body["description"]["en-GB"]
    title = body["title"]["en-GB"]
    back = (
        "Reply *BACK* to go to the previous question."
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
    if cardType == "ROADBLOCK":
        path = body["_links"]["self"]["href"]
    elif not next_question:
        path = ""
    else:
        path = body["_links"]["next"]["href"]
    if "step" in body.keys():
        step = body["step"]
    else:
        step = ""
    if cardType == "CHOICE":
        resource = pdf_resource(body)
        option = body["options"][0]["text"]["en-GB"]
        optionslist = []
        index = 0
        length = len(body["options"])
        while index < length:
            optionslist.append(body["options"][index]["text"]["en-GB"])
            index += 1
        choiceContext = optionslist[:]
        for i in range(len(optionslist)):
            optionslist[i] = f"*{i+1}*. {optionslist[i]}"
        choices = "\n".join(optionslist)
        extra_message = (
            f"Choose the option that matches your answer. Eg, *1* for *{option}*"
        )
        if explanations != "":
            message = (
                f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}\n{explain}"
            )
        else:
            message = f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}"
        body = {}
        body["choices"] = length
        body["choiceContext"] = choiceContext
        body["resource"] = resource
    elif cardType == "TEXT":
        message = f"{description}\n\n{textcontinue}\n\n{back}"
        body = {}
    elif cardType == "ROADBLOCK":
        message = f"{description}"
        body = {}
    elif cardType == "REPORT":
        CTA = (
            "Reply:\n\n*1* - *CHECK* to check another symptom\n\n"
            "*2* - *ASK* to ask the helpdesk a question\n\n"
            "*3* - *MENU* for the MomConnect menu 📌"
        )
        message = f"{description}\n\n{CTA}"
        body = {}
    else:
        placeholder = body["cardAttributes"]["placeholder"]["en-GB"]
        message = f"{description}\n\n_{placeholder}_\n\n{back}"
        format = body["cardAttributes"]["format"]
        if format == "integer":
            max = get_max(body)[0]
            max_error = get_max(body)[1]
            min = get_min(body)[0]
            min_error = get_min(body)[1]
            if get_min(body)[2] == "regex":
                pattern = min
            else:
                pattern = ""
        else:
            max = min = None
            max_error = min_error = ""
            pattern = ""
        body = {}
        body["choices"] = None
        body["formatType"] = format
        body["max"] = max
        body["max_error"] = max_error
        body["min"] = min
        body["min_error"] = min_error
        body["pattern"] = pattern

    body["message"] = message
    body["explanations"] = explanations
    body["step"] = step
    body["optionId"] = optionId
    body["path"] = path
    body["cardType"] = cardType
    body["title"] = title
    body["description"] = description
    body["pdf_media_id"] = pdf_media_id
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


def pdf_resource(data):
    try:
        content_url = data["_links"]["resources"][0]["href"]
        return content_url
    except KeyError:
        return ""


def pdf_endpoint(data):
    json_string = json.dumps(data)
    encoded = urllib.parse.quote(json_string.encode("utf-8"))
    url = reverse("ada-reports")
    reverse_url = f"{url}?payload={encoded}"
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
