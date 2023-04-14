from unittest import TestCase

from ndoh_hub.utils import msisdn_to_whatsapp_id, normalise_msisdn


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
