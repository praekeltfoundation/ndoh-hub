import json
from unittest import TestCase

import pytest
import responses

from eventstore import models
from ndoh_hub.utils import (
    msisdn_to_whatsapp_id,
    normalise_msisdn,
    send_whatsapp_template_message,
    update_turn_contact_details,
)


class TestNormaliseMsisdn(TestCase):
    def test_normalise_msisdn(self):
        """
        Normalises the input string into E164 format
        """
        self.assertEqual(normalise_msisdn("082 000 1001"), "+27820001001")
        self.assertEqual(normalise_msisdn("27820001001"), "+27820001001")
        self.assertEqual(normalise_msisdn("+27820001001"), "+27820001001")


class TestMsisdnToWhatsapp(TestCase):
    def test_msisdn_to_whatsapp_id(self):
        """
        Converts MSISDN to WhatsApp ID
        """
        self.assertEqual(msisdn_to_whatsapp_id("082 000 1001"), "27820001001")
        self.assertEqual(msisdn_to_whatsapp_id("27820001001"), "27820001001")
        self.assertEqual(msisdn_to_whatsapp_id("+27820001001"), "27820001001")


class TestUpdateTurnContactDetails(TestCase):
    @responses.activate
    def test_update_turn_contact_details(self):
        """
        Should call the turn api with the correct body
        """
        responses.add(
            method=responses.PATCH,
            url="http://turn/v1/contacts/27820001001",
            json={},
            status=200,
        )

        update_turn_contact_details("27820001001", {"field": "new value"})

        request = json.loads(responses.calls[0].request.body)
        self.assertEqual(
            request,
            {"field": "new value"},
        )


@pytest.mark.django_db
class TestSendWhatsappTemplateMessage(TestCase):
    @responses.activate
    def test_send_whatsapp_template_message_number_on_whatsapp(self):
        """
        Send a template to Whatsapp
        """
        parameters = {"type": "text", "text": "test template send"}
        namespace = "test"
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

        preferred_channel, status_id = send_whatsapp_template_message(
            msisdn, namespace, template_name, parameters
        )

        self.assertEqual(preferred_channel, "WhatsApp")

        status_count = models.WhatsAppTemplateSendStatus.objects.count()
        self.assertEqual(status_count, 0)

        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_send_whatsapp_template_message_number_on_whatsapp_save_status(self):
        """
        Send a template to Whatsapp
        """
        parameters = {"type": "text", "text": "test template send"}
        namespace = "test"
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

        preferred_channel, status_id = send_whatsapp_template_message(
            msisdn, namespace, template_name, parameters, save_status_record=True
        )

        self.assertEqual(preferred_channel, "WhatsApp")

        status = models.WhatsAppTemplateSendStatus.objects.get(id=status_id)
        self.assertEqual(status.message_id, "gBEGkYiEB1VXAglK1ZEqA1YKPrU")

        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_send_whatsapp_template_message_number_not_on_whatsapp(self):
        """
        Send a template to Whatsapp
        """
        parameters = {"type": "text", "text": "test template send"}
        namespace = "test"
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

        preferred_channel, status_id = send_whatsapp_template_message(
            msisdn, namespace, template_name, parameters
        )

        self.assertEqual(preferred_channel, "SMS")
        self.assertIsNone(status_id)

        self.assertEqual(len(responses.calls), 3)
        request = json.loads(responses.calls[0].request.body)
        self.assertEqual(
            request,
            {"is_fallback_active": False},
        )
        request = json.loads(responses.calls[2].request.body)
        self.assertEqual(
            request,
            {"is_fallback_active": True},
        )
