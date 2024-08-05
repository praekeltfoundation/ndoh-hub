import logging
import urllib

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from aaq.serializers import (
    AddFeedbackSerializer,
    InboundCheckSerializer,
    SearchSerializer,
    UrgencyCheckSerializer,
)

from .tasks import send_feedback_task

logger = logging.getLogger(__name__)


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def get_first_page(request, *args, **kwargs):
    if request.data == {"question": ""}:
        json_msg = {
            "message": "Non-text Input Detected",
        }
        return Response(json_msg, status=status.HTTP_202_ACCEPTED)

    serializer = InboundCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data["question"]
    url = urllib.parse.urljoin(settings.AAQ_CORE_API_URL, "/inbound/check")
    payload = {"text_to_match": f"{question}"}
    headers = {
        "Authorization": settings.AAQ_CORE_INBOUND_CHECK_AUTH,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    feedback_secret_key = response.json()["feedback_secret_key"]
    inbound_secret_key = response.json()["inbound_secret_key"]
    inbound_id = response.json()["inbound_id"]
    top_responses = response.json()["top_responses"]

    if top_responses == []:
        json_msg = {
            "message": "Gibberish Detected",
            "body": {},
            "feedback_secret_key": feedback_secret_key,
            "inbound_secret_key": inbound_secret_key,
            "inbound_id": inbound_id,
        }
        return Response(json_msg, status=status.HTTP_202_ACCEPTED)

    json_msg = {}
    body_content = {}
    message_titles = []

    for count, (id, title, content) in enumerate(top_responses, start=1):
        body_content[f"{count}"] = {"text": content, "id": id}
        message_titles.append(f"*{count}* - {title}")

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "feedback_secret_key": feedback_secret_key,
        "inbound_secret_key": inbound_secret_key,
        "inbound_id": inbound_id,
    }
    if "next_page_url" in response.json():
        json_msg["next_page_url"] = response.json()["next_page_url"]

    return Response(json_msg, status=status.HTTP_202_ACCEPTED)


@api_view(("PUT",))
@renderer_classes((JSONRenderer,))
def add_feedback(request, *args, **kwargs):
    serializer = AddFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    feedback_secret_key = serializer.validated_data["feedback_secret_key"]
    inbound_id = serializer.validated_data["inbound_id"]
    feedback_type = serializer.validated_data["feedback"]["feedback_type"]

    kwargs = {}
    if "faq_id" in serializer.validated_data["feedback"]:
        kwargs["faq_id"] = serializer.validated_data["feedback"]["faq_id"]
    elif "page_number" in serializer.validated_data["feedback"]:
        kwargs["page_number"] = serializer.validated_data["feedback"]["page_number"]
    send_feedback_task.delay(feedback_secret_key, inbound_id, feedback_type, **kwargs)

    return Response(status=status.HTTP_202_ACCEPTED)


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def check_urgency(request, *args, **kwargs):
    serializer = UrgencyCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data["question"]
    url = urllib.parse.urljoin(settings.AAQ_UD_API_URL, "/inbound/check")
    payload = {"text_to_match": f"{question}"}
    headers = {
        "Authorization": settings.AAQ_UD_INBOUND_CHECK_AUTH,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    urgency_score = response.json()["urgency_score"]
    json_msg = {
        "urgency_score": urgency_score,
    }

    return_data = json_msg
    return Response(return_data, status=status.HTTP_202_ACCEPTED)


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def search(request, *args, **kwargs):
    serializer = SearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    query_text = serializer.validated_data["query_text"]
    generate_llm_response = serializer.validated_data["generate_llm_response"]
    query_metadata = serializer.validated_data["query_metadata"]
    url = urllib.parse.urljoin(settings.AAQ_V2_API_URL, "search")
    payload = {
        "query_text": query_text,
        "generate_llm_response": generate_llm_response,
        "query_metadata": query_metadata,
    }
    headers = {
        "Authorization": settings.AAQ_V2_AUTH,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    query_id = response.json()["query_id"]
    feedback_secret_key = response.json()["feedback_secret_key"]
    search_results = response.json()["search_results"]

    if search_results == {}:
        json_msg = {
            "message": "Gibberish Detected",
            "body": {},
            "feedback_secret_key": feedback_secret_key,
            "query_id": query_id,
        }
        return Response(json_msg, status=status.HTTP_200_OK)

    json_msg = {}
    body_content = {}
    message_titles = []

    for key, value in search_results.items():
        text = value["text"]
        id = value["id"]
        title = value["title"]

        body_content[key] = {"text": text, "id": id}
        message_titles.append(f"*{key}* - {title}")

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "feedback_secret_key": feedback_secret_key,
        "query_id": query_id,
    }

    return Response(json_msg, status=status.HTTP_200_OK)
