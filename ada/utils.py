from __future__ import absolute_import, division

import requests
from django.conf import settings
from temba_client.v2 import TembaClient

from .models import AdaAssessment

rapidpro = None
if settings.RAPIDPRO_URL and settings.RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)


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
    head = {
        "x-ada-clientId": "xxxxx ",
        "x-ada-userId": "xxxx",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = path
    response = requests.request("POST", path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def post_to_ada_start_assessment(body):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = settings.ADA_START_ASSESSMENT_URL
    response = requests.request("POST", path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def post_to_ada_next_dialog(body):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = body["_links"]["startAssessment"]["href"]
    response = requests.request("POST", path, json=body, headers=head)
    response.raise_for_status()
    response = response.json()
    return response


def get_from_ada(body):
    # Use assessementid to get first question
    path = body["_links"]["startAssessment"]["href"]
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }

    payload = {}
    response = requests.request("GET", path, json=payload, headers=head).json()
    return response


def format_message(body):
    description = body["description"]["en-US"]
    title = body["title"]["en-US"]
    back = (
        "Enter *back* to go to the previous question or *abort* to end the assessment"
    )
    cardType = body["cardType"]
    if "options" in body.keys() and cardType != "CHOICE":
        optionId = body["options"][0]["optionId"]
    else:
        optionId = ""
    path = body["_links"]["next"]["href"]
    if "step" in body.keys():
        step = body["step"]
    else:
        step = ""
    if cardType == "CHOICE":
        option = body["options"][0]["text"]["en-US"]
        optionslist = []
        index = 0
        length = len(body["options"])
        while index < length:
            optionslist.append(body["options"][index]["text"]["en-US"])
            index += 1
        choices = "\n".join(optionslist)
        extra_message = (
            f"Choose the option that matches your answer. Eg, 1 for {option}"
        )
        message = f"{description}\n\n{choices}\n\n{extra_message}\n\n{back}"
        body = {}
        body["choices"] = length
    else:
        message = f"{description}\n\n{back}"
        body = {}
        body["choices"] = ""
    body["message"] = message
    body["step"] = step
    body["optionId"] = optionId
    body["path"] = path
    body["cardType"] = cardType
    body["title"] = title
    return body


def get_message(payload):
    contact_uuid = (payload["contact_uuid"],)
    step = payload["step"]
    value = payload["value"]
    optionId = payload["optionId"]
    if value != "":
        if value == "back":
            path = get_path(payload)
            request = build_rp_request(payload)
            ada_response = previous_question(request, path)
        else:
            path = get_path(payload)
            request = build_rp_request(payload)
            ada_response = post_to_ada(request, path)
    elif payload["value"] == "":
        request = build_rp_request(payload)
        response = post_to_ada_start_assessment(request)
        path = get_path(response)
        step = get_step(response)
        payload["path"] = path
        payload["step"] = step
        request = build_rp_request(payload)
        ada_response = post_to_ada(request, path)

        # TODO: save to DB here
    if value != "" and value != "back":
        response_data = AdaAssessment(contact_uuid, step, value, optionId)
        response_data.save()
    try:
        report = ada_response["_links"]["report"]
        response = get_report(report)
        return response
    except KeyError:
        pass
    message = format_message(ada_response)
    return message


def get_path(body):
    if "path" in body.keys():
        path = body["path"]
    else:
        path = body["_links"]["startAssessment"]["href"]
    return path


def get_step(body):
    step = body["step"]
    return step


# This returns the report of the assessment
def get_report(body):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = body["_links"]["report"]["href"]
    payload = {}
    response = requests.request("GET", path, json=payload, headers=head)
    return response


# Go back to previous question
def previous_question(body, path):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = path
    path = path.replace("/next", "/previous")
    response = requests.request("POST", path, json=body, headers=head)
    response = response.json()
    return response


# Abort assessment
def abort_assessment(body):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = body["path"]
    path = path.replace("dialog/next", "/abort")
    payload = {}
    response = requests.request("PUT", path, json=payload, headers=head).json()
    return response
