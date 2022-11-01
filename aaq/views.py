import logging
from urllib.parse import urljoin
import requests
import json
import time
from django.http import JsonResponse
from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from .tasks import send_feedback_task

logger = logging.getLogger(__name__)


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def get_first_page(request, *args, **kwargs):
    url = f"{settings.AAQ_CORE_API_URL}/inbound/check"
    #TODO: Replace this hardcoded payload with one from flow
    payload = {"text_to_match": "I am pregnant and out of breath"}
    headers = {
        "Authorization": settings.AAQ_CORE_API_AUTH,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    top_responses = response.json()["top_responses"]

    json_msg = {}
    body_content = {}
    message_titles = []

    counter = 0
    for id, title, content in top_responses:
        counter += 1

        body_content[f"{counter}"] = {"text": content, "id": id}
        message_titles.append(f"*{counter}* - {title}")

    next_page_url = response.json()["next_page_url"]
    feedback_secret_key = response.json()["feedback_secret_key"]
    inbound_secret_key = response.json()["inbound_secret_key"]
    inbound_id = response.json()["inbound_id"]

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "next_page_url": next_page_url,
        "feedback_secret_key": feedback_secret_key,
        "inbound_secret_key": inbound_secret_key,
        "inbound_id": inbound_id,
    }

    return_data = json_msg
    return Response(return_data, status=status.HTTP_202_ACCEPTED)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def get_second_page(request, inbound_id, page_id):
    # TODO: check if I can get this URL also part of the definition above
    inbound_secret_key = request.GET.get("inbound_secret_key")
    url = f"{settings.AAQ_CORE_API_URL}/inbound/{inbound_id}/{page_id}?inbound_secret_key={inbound_secret_key}"
    headers = {
        "Authorization": settings.AAQ_CORE_API_AUTH,
        "Content-Type": "application/json",
    }
    json_msg = {}
    body_content = {}
    message_titles = []

    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        response.raise_for_status()
    top_responses = response.json()["top_responses"]

    counter = 0
    for id, title, content in top_responses:
        counter += 1

        body_content[f"{counter}"] = {"text": content, "id": id}
        message_titles.append(f"*{counter}* - {title}")

    next_page_url = response.json()["next_page_url"]
    feedback_secret_key = response.json()["feedback_secret_key"]
    inbound_secret_key = response.json()["inbound_secret_key"]
    inbound_id = response.json()["inbound_id"]

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "next_page_url": next_page_url,
        "feedback_secret_key": feedback_secret_key,
        "inbound_secret_key": inbound_secret_key,
        "inbound_id": inbound_id,
    }

    # return_data = body_content
    return_data = json_msg
    return Response(return_data, status=status.HTTP_202_ACCEPTED)


@api_view(("PUT",))
@renderer_classes((JSONRenderer,))
def add_feedback(request, *args, **kwargs):
    json_data = json.loads(request.body)
    feedback_secret_key = json_data["feedback_secret_key"]
    inbound_id = json_data["inbound_id"]
    feedback_type = json_data["feedback"]["feedback_type"]
    faq_id = None
    page_number = None
    if "faq_id" in json_data["feedback"]:
        faq_id = json_data["feedback"]["faq_id"]
        send_feedback_task.apply_async(
            args=[feedback_secret_key, inbound_id, feedback_type],
            kwargs={
                "faq_id": faq_id,
            },
            countdown=5,
        )
    if "page_number" in json_data["feedback"]:
        page_number = json_data["feedback"]["page_number"]
        send_feedback_task.apply_async(
            args=[feedback_secret_key, inbound_id, feedback_type],
            kwargs={
                "page": page_number,
            },
            countdown=5,
        )

    return Response(status=status.HTTP_202_ACCEPTED)
