from unittest import TestCase

import responses

from ndoh_hub.utils import (
    msisdn_to_whatsapp_id,
    normalise_msisdn,
    send_whatsapp_template_message,
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
            method=responses.POST,
            url="http://turn/v1/messages",
            json={"messages": [{"id": "gBEGkYiEB1VXAglK1ZEqA1YKPrU"}]},
            status=200,
        )

        response = send_whatsapp_template_message(
            msisdn, namespace, template_name, parameters
        )

        self.assertEqual(response, "Whatsapp")

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
            method=responses.POST,
            url="http://turn/v1/messages",
            json={"error": {"code": 1013}},
        )

        response = send_whatsapp_template_message(
            msisdn, namespace, template_name, parameters
        )

        self.assertEqual(response, "SMS")
