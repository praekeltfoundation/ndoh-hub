import json
import logging
import urllib
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from aaq.serializers import InboundCheckSerializer, UrgencyCheckSerializer

from .tasks import send_feedback_task

logger = logging.getLogger(__name__)


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def get_first_page(request, *args, **kwargs):

    serializer = InboundCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    question = serializer.validated_data["question"]
    url = urllib.parse.urljoin(settings.AAQ_CORE_API_URL, "/inbound/check")
    payload = {"text_to_match": f"{question}"}
    headers = {
        "Authorization": settings.AAQ_CORE_INBOUND_CHECK_TOKEN,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    top_responses = response.json()["top_responses"]

    json_msg = {}
    body_content = {}
    message_titles = []

    for count, (id, title, content) in enumerate(top_responses, start=1):
        body_content[f"{count}"] = {"text": content, "id": id}
        message_titles.append(f"*{count}* - {title}")

    feedback_secret_key = response.json()["feedback_secret_key"]
    inbound_secret_key = response.json()["inbound_secret_key"]
    inbound_id = response.json()["inbound_id"]

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "feedback_secret_key": feedback_secret_key,
        "inbound_secret_key": inbound_secret_key,
        "inbound_id": inbound_id,
    }
    if "next_page_url" in response.json():
        json_msg["next_page_url"] = response.json()["next_page_url"]

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


@api_view(("POST",))
@renderer_classes((JSONRenderer,))
def check_urgency(request, *args, **kwargs):
    serializer = UrgencyCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data["question"]
    url = urllib.parse.urljoin(settings.AAQ_UD_API_URL, "/inbound/check")
    payload = {"text_to_match": f"{question}"}
    headers = {
        "Authorization": settings.AAQ_UD_INBOUND_CHECK_TOKEN,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    urgency_score = response.json()["urgency_score"]
    json_msg = {
        "urgency_score": urgency_score,
    }

    return_data = json_msg
    return Response(return_data, status=status.HTTP_202_ACCEPTED)
