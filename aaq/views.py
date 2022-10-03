import logging
from urllib.parse import urljoin
import requests
import json

from django.conf import settings
from rest_framework import generics, status

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



class AaqFaqViewSet(generics.GenericAPIView):

    serializer_class = BaselineSurveyResultSerializer

    queryset = AaqFaq.objects.all()

    def post(self, request, *args, **kwargs):

        serializer = MqrEndlineChecksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return_data = "post test"
        return Response(return_data, status=status.HTTP_202_ACCEPTED)

    def get(self, request, *args, **kwargs):
        url = "https://mc-aaq-core-prd.ndoh-k8s.prd-p6t.org/inbound/check"

        payload = {
            "text_to_match": "I am pregnant and out of breath",
            "return_scoring": "true"
        }
        headers = {
            "Authorization": "Bearer aBZLwGVGfU5Tb9vNRtsdV7Gaxo5uxLXJ",
            "Content-Type": "application/json"
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        top_responses = response.json()["top_responses"]
        numbers = []
        message_body = """*Here are some topics that might answer your question*
            Reply with a number.

            """
        json_msg = {
            "message": "1. faq title 1 \n 2. faq title 2",
            "body": {
                "1": {"text": "faq body 1", "id": 1},
                "2": {"text": "faq body 2", "id": 2},
                "3": {"text": "faq body 3", "id": 3},
            }
            }
      #  message_content =  "1. faq title 1 \n 2. faq title 2"
      #  body_content = {
      #          "1": {"text": "faq body 1", "id": 1},
      #          "2": {"text": "faq body 2", "id": 2},
      #          "3": {"text": "faq body 3", "id": 3},
      #      }
        body_content = {}
        message_titles = []
            
        counter = 0
        for id, title, content in top_responses:
            counter += 1
            
            body_content[f"{counter}"] = {"text": content, "id": id}
            message_titles.append(title)
                        
        json_msg = {
            "message": "\nhaaaaai".join(message_titles),
            "body": body_content,
            
        }
        

        #return_data = body_content
        return_data = json_msg     
        return Response(return_data, status=status.HTTP_202_ACCEPTED)
   