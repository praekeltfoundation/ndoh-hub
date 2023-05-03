from __future__ import absolute_import, division

import json
import posixpath
import re
import tempfile
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


def displayTitle(title):
    text = [
        "Disclaimer",
        "Terms & Conditions and Privacy Policy",
        "Sharing your health data",
    ]
    if title in text:
        return True
    else:
        return False


def backCTA(step):
    if step == 1:
        return "Reply *EXIT* to exit the symptom checker."
    else:
        return "Reply *BACK* to go to the previous question."


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
    if response.status_code == 410:
        return response.status_code
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
    explain = "I don't understand what this means."
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
    back = backCTA(step)
    if cardType == "CHOICE":
        resource = pdf_resource(body)
        optionslist = []
        index = 0
        length = len(body["options"])
        while index < length:
            optionslist.append(body["options"][index]["text"]["en-GB"])
            index += 1

        if explanations != "":
            length += 1
            optionslist.append(explain)

        choiceContext = optionslist[:]
        for i in range(len(optionslist)):
            optionslist[i] = f"*{i+1} -* {optionslist[i]}"
        choices = "\n".join(optionslist)
        message = f"{description}\n\n{choices}\n\n{back}"
        body = {}
        body["choices"] = length
        body["choiceContext"] = choiceContext
        body["resource"] = resource
    elif cardType == "TEXT":
        message = f"{description}\n\n{textcontinue}\n{back}"
        body = {}
    elif cardType == "ROADBLOCK":
        message = f"{description}"
        body = {}
    elif cardType == "REPORT":
        CTA = (
            "Reply:\n*CHECK* if you would like to check another symptom\n"
            "*MENU* for the MomConnect menu 📌"
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

    body["description"] = description
    body["pdf_media_id"] = pdf_media_id
    checkerTitle = displayTitle(title)
    title = f"*{title}*"
    if checkerTitle:
        body["title"] = title
    else:
        body["title"] = ""
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


def get_edc_report(report_id, contact_uuid):
    head = get_header_edc(contact_uuid)
    payload = {}
    path = urljoin(settings.ADA_EDC_REPORT_URL, report_id)
    response = requests.get(path, json=payload, headers=head)
    response.raise_for_status()
    return response.json()


def upload_edc_media(report, study_id, record_id, field_id, token):
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Accept": "application/hal+json",
    }
    study_id = study_id
    record = "record"
    record_id = record_id
    study_data_point = "study-data-point"
    field_id = field_id
    path = posixpath.join(study_id, record, record_id, study_data_point, field_id)
    report_name = record_id + "_" + "report"
    report_name = clean_filename(report_name)
    url = urljoin(settings.ADA_EDC_STUDY_URL, path)
    nullValues = json.dumps(report, indent=2).replace("null", "None")
    tobyte = nullValues.encode("utf-8")
    file = tempfile.NamedTemporaryFile()
    report_file = file.name
    file.write(tobyte)
    file.seek(0)

    response = requests.post(
        url,
        files={
            "upload_file": (report_name, open(report_file, "rb"), "application/pdf")
        },
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


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


def get_header_edc(contact_uuid):
    head = {
        "x-ada-clientId": settings.X_ADA_CLIENTID,
        "x-ada-userId": contact_uuid,
        "Accept-Language": "en-GB",
        "Accept": "application/json",
        "Content-Type": "application/pdf",
    }
    return head


def create_castor_record(token):
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Accept": "application/json",
    }
    data = {"institute_id": settings.ADA_EDC_INSTITUTE_ID}
    path = urljoin(settings.ADA_EDC_STUDY_URL, f"{settings.ADA_EDC_STUDY_ID}/record")
    response = requests.post(path, json=data, headers=headers).json()

    return response["record_id"]


def submit_castor_data(token, record_id, field, value):
    headers = {
        "Authorization": "Bearer {}".format(token),
        "Accept": "application/json",
    }
    data = {"field_value": value}
    path = urljoin(
        settings.ADA_EDC_STUDY_URL,
        f"{settings.ADA_EDC_STUDY_ID}/record/{record_id}/study-data-point/{field}",
    )
    requests.post(path, json=data, headers=headers)


def clean_filename(file_name):
    file_name = str(file_name).strip().replace(" ", "_")
    return re.sub(r"(?u)[^-\w.]", "", file_name)
