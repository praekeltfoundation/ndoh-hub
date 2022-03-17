from __future__ import absolute_import, division


import requests
from django.conf import settings
from temba_client.v2 import TembaClient

from .models import AdaAssessment

rapidpro = None
if settings.RAPIDPRO_URL and settings.RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)


def get_rp_payload(body):
    return body


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
    if "options" in body.keys():
        optionId = body["options"][0]["optionId"]
    else:
        optionId = ""
    if "value" in body.keys():
        value = body["value"]
    else:
        value = ""

    if cardType != "":
        if cardType == "TEXT":
            payload = {"step": step}
        elif cardType == "TERMS_CONDITIONS":
            payload = {"step": step, ":answer": {"optionId": optionId}}
        elif cardType == "INPUT":
            payload = {"step": step, "answer": {"value": value}}
        elif cardType == "CHOICE":
            payload = {"step": step, "answer": {"optionId": {"optionId": value - 1}}}
    else:
        payload = {}

    return payload


def post_to_ada(body, path):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
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
    path = "/assessments"
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
    description = body["description"]["en-GB"]
    back = (
        "Enter *back* to go to the previous question or *abort* to end the assessment"
    )
    cardType = body["cardType"]
    optionId = body["options"][0]["optionId"]
    path = body["_links"]["next"]["href"]
    if "step" in body.keys():
        step = body["step"]
    else:
        step = ""
    if cardType == "CHOICE":
        options = body["options"][0]["value"]
        optionslist = []
        index = 0
        length = len(body["options"])
        while index < length:
            optionslist.append(body["options"][index]["value"])
            index += 1
        choices = "\n".join(optionslist)
        extra_message = (
            f"Choose the option that matches your answer. Eg, 1 for {options}"
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
    return body


def get_message(payload):
    if payload["value"] != "":
        if payload["value"] == "back":
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
        ada_response = get_from_ada(response)

        # TODO: save to DB here
        # response_data = AdaAssessment(uuid, step, value, optionId)
        # response_data.save()
    try:
        report = ada_response["_links"]["report"]
        response = get_report(report)
        return response
    except KeyError:
        pass
    message = format_message(ada_response)
    return message


def get_path(body):
    path = body["path"]
    return path


# This returns the report of the assessment
def get_report(body):
    head = {
        "x-ada-clientId": "praekelt ",
        "x-ada-userId": "whatsapp-id",
        "Accept-Language": "en-GB",
        "Accept": "application/json",
    }
    path = ["_links"]["report"]["href"]
    payload = {}
    response = requests.request("GET", path, json=payload, headers=head)
    return response

#Go back to previous question
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
