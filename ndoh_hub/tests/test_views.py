import json

import responses
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SendWhatsappTemplateTests(APITestCase):
    url = reverse("send-whatsapp-template")

    @responses.activate
    def test_send_whatsapp_template_unauthorized_user(self):
        """
        unauthorized user access denied
        Returns: status code 401

        """
        responses.add(
            method=responses.POST,
            url="http://turn/v1/messages",
            status=401,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @responses.activate
    def test_send_whatsapp_template_message_number_on_whatsapp(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        parameters = [{"type": "text", "text": "test template send"}]
        msisdn = "+27820001001"
        template_name = "test template"

        responses.add(
            method=responses.PATCH,
            url="http://turn/v1/contacts/27820001001",
            json={},
            status=200,
        )

        responses.add(
            method=responses.POST,
            url="http://turn/v1/messages",
            json={"messages": [{"id": "gBEGkYiEB1VXAglK1ZEqA1YKPrU"}]},
            status=200,
        )

        response = self.client.post(
            self.url,
            data={
                "msisdn": msisdn,
                "template_name": template_name,
                "parameters": parameters,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["preferred_channel"], "WhatsApp")

        request = json.loads(responses.calls[1].request.body)
        self.assertEqual(
            request,
            {
                "to": "27820001001",
                "type": "template",
                "template": {
                    "namespace": "test-namespace",
                    "name": "test template",
                    "language": {"policy": "deterministic", "code": "en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": "test template send"}
                            ],
                        }
                    ],
                },
            },
        )

    @responses.activate
    def test_send_whatsapp_template_message_number_not_on_whatsapp(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        msisdn = "+27820001001"
        template_name = "test template"

        responses.add(
            method=responses.PATCH,
            url="http://turn/v1/contacts/27820001001",
            json={},
            status=200,
        )

        responses.add(
            method=responses.POST,
            url="http://turn/v1/messages",
            json={
                "errors": [
                    {
                        "code": 1013,
                        "details": "Recipient is not a valid WhatsApp user",
                        "title": "User is not valid",
                    }
                ],
                "meta": {
                    "api_status": "stable",
                    "backend": {"name": "WhatsApp", "version": "latest"},
                    "version": "4.412.3",
                },
            },
        )

        response = self.client.post(
            self.url,
            data={
                "msisdn": msisdn,
                "template_name": template_name,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["preferred_channel"], "SMS")

        request = json.loads(responses.calls[1].request.body)
        self.assertEqual(
            request,
            {
                "to": "27820001001",
                "type": "template",
                "template": {
                    "namespace": "test-namespace",
                    "name": "test template",
                    "language": {"policy": "deterministic", "code": "en"},
                    "components": [],
                },
            },
        )

    @responses.activate
    def test_send_whatsapp_template_message_with_media(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        media = {"filename": "myfile.pdf", "id": "media-uuid"}
        msisdn = "+27820001001"
        template_name = "test template"

        responses.add(
            method=responses.PATCH,
            url="http://turn/v1/contacts/27820001001",
            json={},
            status=200,
        )

        responses.add(
            method=responses.POST,
            url="http://turn/v1/messages",
            json={"messages": [{"id": "gBEGkYiEB1VXAglK1ZEqA1YKPrU"}]},
            status=200,
        )

        response = self.client.post(
            self.url,
            data={
                "msisdn": msisdn,
                "template_name": template_name,
                "media": media,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["preferred_channel"], "WhatsApp")

        request = json.loads(responses.calls[1].request.body)
        self.assertEqual(
            request,
            {
                "to": "27820001001",
                "type": "template",
                "template": {
                    "namespace": "test-namespace",
                    "name": "test template",
                    "language": {"policy": "deterministic", "code": "en"},
                    "components": [
                        {
                            "type": "header",
                            "parameters": [
                                {
                                    "type": "document",
                                    "document": {
                                        "filename": "myfile.pdf",
                                        "id": "media-uuid",
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
        )

    @responses.activate
    def test_send_whatsapp_template_message_invalid(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            data={
                "parameters": [{"something": "else"}],
                "media": {"something": "else"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "msisdn": ["This field is required."],
                "template_name": ["This field is required."],
                "parameters": {
                    "0": {
                        "type": ["This field is required."],
                        "text": ["This field is required."],
                    }
                },
                "media": {
                    "filename": ["This field is required."],
                    "id": ["This field is required."],
                },
            },
        )
