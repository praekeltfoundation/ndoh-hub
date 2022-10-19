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

from rest_framework.viewsets import GenericViewSet
from mqr.serializers import (
    FaqMenuSerializer,
    FaqSerializer,
    FirstSendDateSerializer,
    MqrEndlineChecksSerializer,
    NextMessageSerializer,
    BaselineSurveyResultSerializer,
)
from ndoh_hub.utils import rapidpro

from .models import AaqFaq

logger = logging.getLogger(__name__)


CORE_API_URL = "https://mc-aaq-core-prd.ndoh-k8s.prd-p6t.org"

def apitest(request):
  time.sleep(1)
  payload = {"message": "Hello from Crowdbotics!"}
  if "task_id" in request.GET:
    payload["task_id"] = request.GET["task_id"]
  return JsonResponse(payload)

@api_view(('POST',))
@renderer_classes((JSONRenderer,))
def get_first_page(request, *args, **kwargs):
    url = f"{CORE_API_URL}/inbound/check"

    payload = {
        "text_to_match": "I am pregnant and out of breath"
    }
    headers = {
        "Authorization": "Bearer aBZLwGVGfU5Tb9vNRtsdV7Gaxo5uxLXJ",
        "Content-Type": "application/json"
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

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def get_second_page(request, inbound_id, page_id):
    #TODO: check if I can get this URL also part of the definition above
    inbound_secret_key = request.GET.get('inbound_secret_key')
    url = f"{CORE_API_URL}/inbound/{inbound_id}/{page_id}?inbound_secret_key={inbound_secret_key}"
    headers = {
        "Authorization": "Bearer aBZLwGVGfU5Tb9vNRtsdV7Gaxo5uxLXJ",
        "Content-Type": "application/json"
    }
    json_msg = {}
    body_content = {}
    message_titles = []

    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        print("CAUGHT HERE") 
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

    #return_data = body_content
    return_data = json_msg    
    return Response(return_data, status=status.HTTP_202_ACCEPTED)    
