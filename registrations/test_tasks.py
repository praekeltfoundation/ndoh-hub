import responses
from django.test import TestCase

from registrations.models import WhatsAppContact
from registrations.tasks import get_whatsapp_contact


class GetWhatsAppContactTests(TestCase):
    @responses.activate
    def test_contact_returned(self):
        """
        If the API returns a contact, the ID should be saved in the database
        """
        self.assertEqual(WhatsAppContact.objects.count(), 0)
        responses.add(
            responses.POST,
            "http://engage/v1/contacts",
            json={
                "contacts": [
                    {"input": "+27820001001", "status": "valid", "wa_id": "27820001001"}
                ]
            },
        )
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "27820001001")

    @responses.activate
    def test_contact_not_returned(self):
        """
        If the API doesn't return a contact, the ID should be blank in the database
        """
        self.assertEqual(WhatsAppContact.objects.count(), 0)
        responses.add(
            responses.POST,
            "http://engage/v1/contacts",
            json={"contacts": [{"input": "+27820001001", "status": "invalid"}]},
        )
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "")

    @responses.activate
    def test_contact_exists_in_database(self):
        """
        If the contact already exists in the database, it should be returned
        """
        WhatsAppContact.objects.create(msisdn="+27820001001", whatsapp_id="27820001001")
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "27820001001")
