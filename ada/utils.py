from __future__ import absolute_import, division

import json
from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings
from django.urls import reverse
from temba_client.v2 import TembaClient

rapidpro = None
if settings.RAPIDPRO_URL and settings.RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)


def get_from_send(payload):
    head = get_header()
    cardType = payload["cardType"]
    body = {"cardType": cardType}
    url = reverse("ada-receive")
    response = requests.post(url, data=json.dumps(body), headers=head)
    return response


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

    if cardType != "" and value != "back":
        if cardType == "TEXT":
            payload = {"step": step}
        elif cardType == "INPUT":
            payload = {"step": step, "value": value}
        elif cardType == "CHOICE":
            payload = {"step": step, "optionId": int(value) - 1}
    elif cardType == "" and step == 0:
        payload = {"step": 0}
    elif value == "back":
        payload = {"step": step}
    else:
        payload = {}

    return payload


def post_to_ada(body, path):
    head = get_header()
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    response = requests.post(path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def post_to_ada_start_assessment(body):
    head = get_header()
    path = f"{settings.ADA_START_ASSESSMENT_URL}/assessments"
    response = requests.post(path, body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def post_to_ada_next_dialog(body):
    head = get_header()
    path = body["_links"]["startAssessment"]["href"]
    response = requests.request("POST", path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def get_from_ada(body):
    # Use assessementid to get first question
    path = body["_links"]["startAssessment"]["href"]
    head = get_header()
    payload = {}
    response = requests.request("GET", path, json=payload, headers=head).json()
    return response


def format_message(body):
    description = body["description"]["en-GB"]
    title = body["title"]["en-GB"]
    back = (
        "Reply *back* to go to the previous question or *abort* to end the assessment"
    )
    textcontinue = "Reply '0' to continue."
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
        choices = "\n".join(optionslist)
        extra_message = (
            f"Choose the option that matches your answer. Eg, 1 for {option}"
        )
        message = f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}"
        body = {}
        body["choices"] = length
    elif cardType == "TEXT":
        message = f"{description}\n\n{textcontinue}\n\n{back}"
        body = {}
    else:
        message = f"{description}\n\n{back}"
        body = {}
        body["choices"] = None
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
    if value != "":
        if value == "back":
            url = reverse("ada-previous-dialog")
        elif value == "abort":
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
    # head = get_header()
    report_id = data["_links"]["report"]["href"]
    qs = "?report_id=" + report_id
    url = reverse("ada-reports")
    reverse_url = url + qs
    # response = requests.post(url, data=json.dumps(data), headers=head)
    return reverse_url


# This returns the report of the assessment
def get_report(path):
    head = get_header()
    # path = data["_links"]["report"]["href"]
    payload = {}
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    response = requests.get(path, json=payload, headers=head)
    return response


# Go back to previous question
def previous_question(body, path):
    head = get_header()
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    path = path.replace("/next", "/previous")
    response = requests.post(path, json=body, headers=head)
    response = response.json()
    return response


# Abort assessment
def abort_assessment(body):
    head = get_header()
    path = body["path"]
    path = urljoin(settings.ADA_START_ASSESSMENT_URL, path)
    path = path.replace("dialog/next", "/abort")
    payload = {}
    response = requests.put(path, json=payload, headers=head).json()
    return response


def get_header():
    head = {
        "x-ada-clientId": settings.X_ADA_CLIENTID,
        "x-ada-userId": settings.X_ADA_USERID,
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    return head
