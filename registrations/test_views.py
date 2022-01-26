import datetime
import json
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from registrations.models import (
    ClinicCode,
    WhatsAppContact,
)


class HUBAPITestCase(TestCase):
    def setUp(self):
        self.normalclient = APIClient()
        # utils.get_today = override_get_today


class AuthenticatedAPITestCase(HUBAPITestCase):

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()

        # Normal User setup
        self.normalusername = "testnormaluser"
        self.normalpassword = "testnormalpass"
        self.normaluser = User.objects.create_user(
            self.normalusername, "testnormaluser@example.com", self.normalpassword
        )
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken.key
        self.normalclient.credentials(HTTP_AUTHORIZATION="Token " + self.normaltoken)


class FacilityCheckViewTests(APITestCase):
    def test_filter_by_code(self):
        ClinicCode.objects.create(
            code="123456", value="123456", uid="cc1", name="test1"
        )
        ClinicCode.objects.create(
            code="654321", value="123456", uid="cc2", name="test2"
        )
        user = User.objects.create_user("test", "test")
        self.client.force_authenticate(user)

        url = reverse("facility-check")
        r = self.client.get(url, {"criteria": "code:123456"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(r.content),
            {
                "title": "FacilityCheck",
                "headers": [
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "code",
                        "column": "code",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "value",
                        "column": "value",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "uid",
                        "column": "uid",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "name",
                        "column": "name",
                        "type": "java.lang.String",
                    },
                ],
                "rows": [["123456", "123456", "cc1", "test1"]],
                "width": 4,
                "height": 1,
            },
        )


class WhatsAppContactCheckViewTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.normalclient.credentials(HTTP_AUTHORIZATION="Bearer %s" % self.normaltoken)

    def test_authentication_required(self):
        """
        Authentication must be provided in order to access the endpoint
        """
        url = reverse("whatsappcontact-list")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can add WhatsApp Contact")
        )
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("registrations.views.get_whatsapp_contact")
    def test_get_statuses(self, task):
        """
        Contacts without whatsapp IDs should return invalid, with IDs valid, and no
        entry in the database, either "processing" for no_wait or do the lookup for wait
        """
        url = reverse("whatsappcontact-list")
        WhatsAppContact.objects.create(msisdn="0820001001")
        WhatsAppContact.objects.create(msisdn="0820001002", whatsapp_id="27820001002")
        task.return_value = {"input": "0820001003", "status": "invalid"}

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can add WhatsApp Contact")
        )
        response = self.normalclient.post(
            url,
            data={
                "blocking": "wait",
                "contacts": ["0820001001", "0820001002", "0820001003"],
            },
        )
        self.assertEqual(
            json.loads(response.content),
            {
                "contacts": [
                    {"input": "0820001001", "status": "invalid"},
                    {"input": "0820001002", "status": "valid", "wa_id": "27820001002"},
                    {"input": "0820001003", "status": "invalid"},
                ]
            },
        )
        task.assert_called_once_with(msisdn="0820001003")

        task.reset_mock()
        response = self.normalclient.post(
            url,
            data={
                "blocking": "no_wait",
                "contacts": ["0820001001", "0820001002", "0820001003"],
            },
        )
        self.assertEqual(
            json.loads(response.content),
            {
                "contacts": [
                    {"input": "0820001001", "status": "invalid"},
                    {"input": "0820001002", "status": "valid", "wa_id": "27820001002"},
                    {"input": "0820001003", "status": "processing"},
                ]
            },
        )

        task.assert_not_called()
        task.delay.assert_called_once_with(msisdn="0820001003")

    def test_prune_contacts_permission_required(self):
        """
        You need to be authenticated and have the correct permission to be able to prune
        whatsapp contacts from the database
        """
        url = reverse("whatsappcontact-prune")
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can prune WhatsApp contact")
        )
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_prune_contacts(self):
        """
        The prune action should delete all contacts older than 7 days from the database
        """
        contact1 = WhatsAppContact.objects.create(
            msisdn="0820001001", whatsapp_id="27820001001"
        )
        contact2 = WhatsAppContact.objects.create(
            msisdn="0820001002", whatsapp_id="27820001002"
        )
        contact2.created = timezone.now() - datetime.timedelta(days=7)
        contact2.save()

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can prune WhatsApp contact")
        )
        url = reverse("whatsappcontact-prune")
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact, contact1)
