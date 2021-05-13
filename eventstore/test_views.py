import base64
import datetime
import hmac
from datetime import date
from hashlib import sha256
from unittest import mock
from urllib.parse import urlencode

import responses
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from pytz import UTC
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase
from temba_client.v2 import TembaClient

from eventstore import tasks
from eventstore.models import (
    PASSPORT_IDTYPE,
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    Covid19TriageStart,
    DBEOnBehalfOfProfile,
    DeliveryFailure,
    EddSwitch,
    Event,
    HealthCheckUserProfile,
    IdentificationSwitch,
    LanguageSwitch,
    Message,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)
from eventstore.serializers import (
    Covid19TriageSerializer,
    Covid19TriageStartSerializer,
    Covid19TriageV2Serializer,
    Covid19TriageV3Serializer,
)


class BaseEventTestCase(object):
    def test_authentication_required(self):
        """
        There must be an authenticated user to make the request
        """
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_required(self):
        """
        The authenticated user must have the correct permissions to make the request
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OptOutViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("optout-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_optout"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new OptOut object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_optout"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "optout_type": OptOut.STOP_TYPE,
                "reason": OptOut.UNKNOWN_REASON,
                "source": "SMS",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [optout] = OptOut.objects.all()
        self.assertEqual(str(optout.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91")
        self.assertEqual(optout.optout_type, OptOut.STOP_TYPE)
        self.assertEqual(optout.reason, OptOut.UNKNOWN_REASON)
        self.assertEqual(optout.source, "SMS")
        self.assertEqual(optout.created_by, user.username)

    @responses.activate
    def test_forget_optout(self):
        """
        Should anonymize the contact's data
        """
        tasks.rapidpro = TembaClient("textit.in", "test-token")
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        responses.add(
            responses.GET,
            f"https://textit.in/api/v2/contacts.json?uuid={contact_id}",
            json={
                "results": [
                    {
                        "uuid": contact_id,
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )
        responses.add(
            responses.DELETE,
            f"https://textit.in/api/v2/contacts.json?uuid={contact_id}",
        )

        msisdnswitch = MSISDNSwitch.objects.create(
            contact_id=contact_id,
            source="POPI USSD",
            old_msisdn="+27820001001",
            new_msisdn="+27820001002",
        )
        identificationswitch = IdentificationSwitch.objects.create(
            contact_id=contact_id,
            source="POPI USSD",
            old_identification_type="passport",
            old_id_number="A12345",
            new_identification_type="passport",
            new_id_number="A54321",
        )
        chwregistration = CHWRegistration.objects.create(
            contact_id=contact_id,
            device_contact_id=contact_id,
            source="CHW USSD",
            id_type="passport",
            passport_number="A12345",
            language="zul",
        )
        prebirthregistration = PrebirthRegistration.objects.create(
            contact_id=contact_id,
            device_contact_id=contact_id,
            source="CHW USSD",
            id_type="passport",
            passport_number="A12345",
            language="zul",
            edd="2020-12-01",
        )
        postbirthregistration = PostbirthRegistration.objects.create(
            contact_id=contact_id,
            device_contact_id=contact_id,
            source="CHW USSD",
            id_type="passport",
            passport_number="A12345",
            language="zul",
            baby_dob="2020-01-01",
        )
        message = Message.objects.create(
            contact_id="27820001001", message_direction=Message.INBOUND
        )
        event = Event.objects.create(recipient_id="27820001001")

        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_optout"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": contact_id,
                "optout_type": OptOut.FORGET_TYPE,
                "reason": OptOut.BABYLOSS_REASON,
                "source": "Optout USSD",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        msisdnswitch.refresh_from_db()
        self.assertEqual(msisdnswitch.old_msisdn, "")
        self.assertEqual(msisdnswitch.new_msisdn, "")

        identificationswitch.refresh_from_db()
        self.assertEqual(identificationswitch.old_id_number, "")
        self.assertEqual(identificationswitch.new_id_number, "")

        chwregistration.refresh_from_db()
        self.assertEqual(chwregistration.passport_number, "")

        prebirthregistration.refresh_from_db()
        self.assertEqual(prebirthregistration.passport_number, "")

        postbirthregistration.refresh_from_db()
        self.assertEqual(postbirthregistration.passport_number, "")

        message.refresh_from_db()
        self.assertEqual(message.contact_id, contact_id)

        event.refresh_from_db()
        self.assertEqual(event.recipient_id, contact_id)

        self.assertEqual(len(responses.calls), 2)


class ForgetContactViewTests(APITestCase):
    url = reverse("forgetcontact")

    @mock.patch("eventstore.views.forget_contact")
    def test_unauthenticated(self, mock_forget_contact):
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        response = self.client.post(self.url, {"contact_id": contact_id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        mock_forget_contact.delay.assert_not_called()

    @mock.patch("eventstore.views.forget_contact")
    def test_invalid_data(self, mock_forget_contact):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {"contact": "123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"contact_id": ["This field is required."]})

        mock_forget_contact.delay.assert_not_called()

    @mock.patch("eventstore.views.forget_contact")
    def test_successful_forget(self, mock_forget_contact):
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {"contact_id": contact_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_forget_contact.delay.assert_called_once_with(contact_id)


class BabySwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("babyswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babyswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new BabySwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babyswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {"contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91", "source": "SMS"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [babyswitch] = BabySwitch.objects.all()
        self.assertEqual(
            str(babyswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(babyswitch.source, "SMS")
        self.assertEqual(babyswitch.created_by, user.username)


class ChannelSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("channelswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_channelswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_channelswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "SMS",
                "from_channel": "SMS",
                "to_channel": "WhatsApp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = ChannelSwitch.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(channelswitch.source, "SMS")
        self.assertEqual(channelswitch.from_channel, "SMS")
        self.assertEqual(channelswitch.to_channel, "WhatsApp")
        self.assertEqual(channelswitch.created_by, user.username)


class MSISDNSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("msisdnswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_msisdnswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_msisdnswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_msisdn": "+27820001001",
                "new_msisdn": "+27820001002",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [msisdnswitch] = MSISDNSwitch.objects.all()
        self.assertEqual(
            str(msisdnswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(msisdnswitch.source, "POPI USSD")
        self.assertEqual(msisdnswitch.old_msisdn, "+27820001001")
        self.assertEqual(msisdnswitch.new_msisdn, "+27820001002")
        self.assertEqual(msisdnswitch.created_by, user.username)


class LanguageSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("languageswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_languageswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new LanguageSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_languageswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_language": "zul",
                "new_language": "xho",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [languageswitch] = LanguageSwitch.objects.all()
        self.assertEqual(
            str(languageswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(languageswitch.source, "POPI USSD")
        self.assertEqual(languageswitch.old_language, "zul")
        self.assertEqual(languageswitch.new_language, "xho")
        self.assertEqual(languageswitch.created_by, user.username)


class EddSwitchViewsettests(APITestCase, BaseEventTestCase):
    url = reverse("eddswitch-list")

    def test_data_validation(self):
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_eddswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_eddswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_edd": "2020-06-06",
                "new_edd": "2020-06-07",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [eddswitch] = EddSwitch.objects.all()
        self.assertEqual(
            str(eddswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(eddswitch.source, "POPI USSD")
        self.assertEqual(eddswitch.old_edd, date(2020, 6, 6))
        self.assertEqual(eddswitch.new_edd, date(2020, 6, 7))
        self.assertEqual(eddswitch.created_by, user.username)


class BabyDobSwitchViewSettests(APITestCase, BaseEventTestCase):
    url = reverse("babydobswitch-list")

    def test_data_validation(self):
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babydobswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babydobswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_baby_dob": "2020-06-06",
                "new_baby_dob": "2020-06-07",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [babydobswitch] = BabyDobSwitch.objects.all()
        self.assertEqual(
            str(babydobswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(babydobswitch.source, "POPI USSD")
        self.assertEqual(babydobswitch.old_baby_dob, date(2020, 6, 6))
        self.assertEqual(babydobswitch.new_baby_dob, date(2020, 6, 7))
        self.assertEqual(babydobswitch.created_by, user.username)


class IdentificationSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("identificationswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_identificationswitch")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new IdentificationSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_identificationswitch")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_identification_type": "passport",
                "new_identification_type": "passport",
                "old_passport_country": "zw",
                "old_passport_number": "A54321",
                "new_passport_country": "other",
                "new_passport_number": "A1234567890123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [identificationswitch] = IdentificationSwitch.objects.all()
        self.assertEqual(
            str(identificationswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(identificationswitch.source, "POPI USSD")
        self.assertEqual(identificationswitch.old_identification_type, "passport")
        self.assertEqual(identificationswitch.old_passport_country, "zw")
        self.assertEqual(identificationswitch.new_passport_country, "other")
        self.assertEqual(identificationswitch.old_dob, None)
        self.assertEqual(identificationswitch.created_by, user.username)


class ResearchOptinSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("researchoptinswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_researchoptinswitch")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ResearchOptinSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_researchoptinswitch")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "POPI USSD",
                "old_research_consent": False,
                "new_research_consent": True,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [researchoptin] = ResearchOptinSwitch.objects.all()
        self.assertEqual(
            str(researchoptin.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(researchoptin.source, "POPI USSD")
        self.assertEqual(researchoptin.old_research_consent, False)
        self.assertEqual(researchoptin.new_research_consent, True)


class PublicRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("publicregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_publicregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_publicregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "language": "zul",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = PublicRegistration.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(channelswitch.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(channelswitch.source, "WhatsApp")
        self.assertEqual(channelswitch.language, "zul")
        self.assertEqual(channelswitch.created_by, user.username)


class PrebirthRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("prebirthregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new PrebirthRegistration object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "zw",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "edd": "2020-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PrebirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.id_type, PASSPORT_IDTYPE)
        self.assertEqual(registration.id_number, "")
        self.assertEqual(registration.passport_country, "zw")
        self.assertEqual(registration.passport_number, "FN123456")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.language, "zul")
        self.assertEqual(registration.edd, datetime.date(2020, 10, 11))
        self.assertEqual(registration.facility_code, "123456")
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

        self.assertFalse(DeliveryFailure.objects.all().exists())

    @responses.activate
    def test_reset_delivery_failures(self):
        """
        Should create a new PrebirthRegistration object in the database and reset
        the delivery failure record if present
        """
        contact_uuid = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        wa_id = "27820001001"

        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)

        DeliveryFailure.objects.create(contact_id=wa_id, number_of_failures=5)

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            f"https://textit.in/api/v2/contacts.json?uuid={contact_uuid}",
            json={
                "results": [
                    {
                        "uuid": contact_uuid,
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": [f"whatsapp:{wa_id}"],
                    }
                ],
                "next": None,
            },
        )

        response = self.client.post(
            self.url,
            {
                "contact_id": contact_uuid,
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "zw",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "edd": "2020-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PrebirthRegistration.objects.all()
        self.assertEqual(str(registration.contact_id), contact_uuid)
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.id_type, PASSPORT_IDTYPE)
        self.assertEqual(registration.id_number, "")
        self.assertEqual(registration.passport_country, "zw")
        self.assertEqual(registration.passport_number, "FN123456")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.language, "zul")
        self.assertEqual(registration.edd, datetime.date(2020, 10, 11))
        self.assertEqual(registration.facility_code, "123456")
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

        [delivery_failure] = DeliveryFailure.objects.all()
        self.assertEqual(delivery_failure.contact_id, wa_id)
        self.assertEqual(delivery_failure.number_of_failures, 0)

    def test_prebirth_other_passport_origin(self):
        """
        Should create a new PrebirthRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "edd": "2020-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PrebirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")


class PMTCTRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("pmtctregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_pmtctregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_pmtct_registration_request(self):
        """
        Should create a new PMTCTRegistration object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_pmtctregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "pmtct_risk": "normal",
                "date_of_birth": "1990-02-03",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PMTCTRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.pmtct_risk, "normal")
        self.assertEqual(registration.date_of_birth, datetime.date(1990, 2, 3))
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

    def test_successful_request_with_null_date_of_birth(self):
        """
        Should create succuess object in the database if dob is null
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_pmtctregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "pmtct_risk": "normal",
                "date_of_birth": None,
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PMTCTRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.pmtct_risk, "normal")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)


class PostbirthRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("postbirthregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new PostbirthRegistration object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "zw",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "baby_dob": "2018-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PostbirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.id_type, PASSPORT_IDTYPE)
        self.assertEqual(registration.id_number, "")
        self.assertEqual(registration.passport_country, "zw")
        self.assertEqual(registration.passport_number, "FN123456")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.language, "zul")
        self.assertEqual(registration.baby_dob, datetime.date(2018, 10, 11))
        self.assertEqual(registration.facility_code, "123456")
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

    def test_postbirth_other_passport_origin(self):
        """
        Should create a new PostbirthRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "baby_dob": "2018-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PostbirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")


class MessagesViewSetTests(APITestCase):
    url = reverse("messages-list")

    def generate_hmac_signature(self, data, key):
        data = JSONRenderer().render(data)
        h = hmac.new(key.encode(), data, sha256)
        return base64.b64encode(h.digest()).decode()

    def test_message_identification_required(self):
        """
        There must be identification of user to make the request
        """
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data, {"detail": "Authentication credentials were not provided."}
        )

    def test_message_authentication_required(self):
        """
        The user needs the `add _message` permission
        in order to make the request

        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        data = {"random": "data"}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {"detail": "You do not have permission to perform this action."},
        )

    def test_message_authentication_errors(self):
        """
        We expect to get auth errors when no user token is added to the querystring,
        but when added the request is made
        """

        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        data = {"random": "data"}

        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token = Token.objects.create(user=user)
        url = "{}?token={}".format(reverse("messages-list"), str(token.key))
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_incorrect_header_request(self):
        """
        If the header doesn't contain a value that we recognise,
        we should return a 400 Bad Request error,
        explaining that we only accept whatsapp and turn webhook types.
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="other",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "X-Turn-Hook-Subscription": [
                    '"other" is not a valid choice for this header.'
                ]
            },
        )

    def test_missing_hook_subscription_header(self):
        """
        If the hook subscription type header is missing, we should return a descriptive
        error
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"X-Turn-Hook-Subscription": ["This header is required."]}
        )

    def test_missing_field_in_inbound_message_request(self):
        """
        If the data is missing a required field, we should return a
        400 Bad Request error explaining that the field is needed
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {"messages": [{"timestamp": "A"}], "statuses": [{"timestamp": "B"}]}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "messages": {
                    0: {
                        "id": ["This field is required."],
                        "type": ["This field is required."],
                        "timestamp": ["Invalid POSIX timestamp."],
                    }
                },
                "statuses": {
                    0: {
                        "id": ["This field is required."],
                        "recipient_id": ["This field is required."],
                        "timestamp": ["Invalid POSIX timestamp."],
                        "status": ["This field is required."],
                    }
                },
            },
        )

    def test_outbound_message_validation(self):
        """
        If there are any errors in the body or headers of the request, we should
        return an error with a suitable description
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"to": ["This field is required."]})

    def test_outbound_message_missing_id(self):
        """
        The header with the message ID is required. If it is not present, a descriptive
        error should be returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {"to": "27820001001"}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"X-WhatsApp-Id": ["This header is required."]})

    def test_successful_inbound_messages_request(self):
        """
        Should create a new Inbound Message object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "messages": [
                {
                    "id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                    "from": "sender-wa-id",
                    "timestamp": "1518694700",
                    "type": "image",
                    "context": {
                        "from": "sender-wa-id-of-context-message",
                        "group_id": "group-id-of-context-message",
                        "id": "message-id-of-context-message",
                        "mentions": ["wa-id1", "wa-id2"],
                    },
                    "image": {
                        "file": "absolute-filepath-on-coreapp",
                        "id": "media-id",
                        "link": "link-to-image-file",
                        "mime_type": "media-mime-type",
                        "sha256": "checksum",
                        "caption": "image-caption",
                    },
                    "location": {
                        "address": "1 Hacker Way, Menlo Park, CA, 94025",
                        "name": "location-name",
                    },
                    "system": {"body": "system-message-content"},
                    "text": {"body": "text-message-content"},
                    "random": "data",
                }
            ]
            * 2
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [messages] = Message.objects.all()
        self.assertEqual(str(messages.contact_id), "sender-wa-id")
        self.assertEqual(
            messages.timestamp, datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)
        ),
        self.assertEqual(messages.id, "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"),
        self.assertEqual(messages.type, "image"),
        self.assertEqual(messages.message_direction, Message.INBOUND),
        self.assertEqual(
            messages.data,
            {
                "context": {
                    "from": "sender-wa-id-of-context-message",
                    "group_id": "group-id-of-context-message",
                    "id": "message-id-of-context-message",
                    "mentions": ["wa-id1", "wa-id2"],
                },
                "image": {
                    "file": "absolute-filepath-on-coreapp",
                    "id": "media-id",
                    "link": "link-to-image-file",
                    "mime_type": "media-mime-type",
                    "sha256": "checksum",
                    "caption": "image-caption",
                },
                "location": {
                    "address": "1 Hacker Way, Menlo Park, CA, 94025",
                    "name": "location-name",
                },
                "system": {"body": "system-message-content"},
                "text": {"body": "text-message-content"},
                "random": "data",
            },
        ),
        self.assertEqual(messages.created_by, user.username)

    def test_successful_inbound_from_fallback_channel(self):
        """
        Save inbound message when subscription is turn and x-turn-event is 1
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "messages": [
                {
                    "id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                    "from": "sender-wa-id",
                    "timestamp": "1518694700",
                    "type": "image",
                    "text": {"body": "text-message-content"},
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_TURN_EVENT="1",
            HTTP_X_TURN_FALLBACK_CHANNEL="1",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [message] = Message.objects.all()
        self.assertEqual(str(message.contact_id), "sender-wa-id")
        self.assertEqual(message.message_direction, Message.INBOUND)

    def test_successful_outbound_messages_request(self):
        """
        Should create a new Outbound Message object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "preview_url": True,
            "render_mentions": True,
            "recipient_type": "individual",
            "to": "whatsapp-id",
            "type": "text",
            "text": {"body": "your-text-message-content"},
            "random": "data",
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
        )
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [messages] = Message.objects.all()
        self.assertEqual(str(messages.contact_id), "whatsapp-id")
        self.assertEqual(messages.id, "message-id"),
        self.assertEqual(messages.type, "text"),
        self.assertEqual(messages.message_direction, Message.OUTBOUND),
        self.assertEqual(
            messages.data,
            {
                "text": {"body": "your-text-message-content"},
                "render_mentions": True,
                "preview_url": True,
                "random": "data",
                "recipient_type": "individual",
            },
        ),
        self.assertEqual(messages.created_by, user.username)
        self.assertFalse(messages.fallback_channel)

    def test_successful_outbound_messages_on_fallback(self):
        """
        Should create a new Outbound Message object in the database with the
        fallback channel flag on
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "preview_url": True,
            "render_mentions": True,
            "recipient_type": "individual",
            "to": "whatsapp-id",
            "type": "text",
            "text": {"body": "your-text-message-content"},
            "random": "data",
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
            HTTP_X_TURN_FALLBACK_CHANNEL="1",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [messages] = Message.objects.all()
        self.assertTrue(messages.fallback_channel)

    @mock.patch("eventstore.views.handle_event")
    def test_successful_events_request(self, mock_handle_event):
        """
        Should create a new Event object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [event] = Event.objects.all()
        self.assertEqual(str(event.message_id), "ABGGFlA5FpafAgo6tHcNmNjXmuSf")
        self.assertEqual(str(event.recipient_id), "16315555555")
        self.assertEqual(event.status, "read")
        self.assertEqual(
            event.timestamp, datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)
        )
        self.assertEqual(event.created_by, user.username)
        self.assertFalse(event.fallback_channel)

        mock_handle_event.assert_not_called()

    @mock.patch("eventstore.views.handle_event")
    def test_successful_events_request_on_fallback_channel(self, mock_handle_event):
        """
        Should create a new Event object in the database with the fallback
        channel flag on
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
            HTTP_X_TURN_FALLBACK_CHANNEL="1",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [event] = Event.objects.all()
        self.assertTrue(event.fallback_channel)

        mock_handle_event.assert_not_called()

    @mock.patch("eventstore.views.handle_event")
    @override_settings(ENABLE_EVENTSTORE_WHATSAPP_ACTIONS=True)
    def test_events_request_calls_handle_event(self, mock_handle_event):
        """
        Should call handle_event if the eventstore whatsapp actions are enabled
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [event] = Event.objects.all()

        mock_handle_event.assert_called_with(event)

    def test_signature_required(self):
        """
        Should see if the signature hook is given,
        otherwise, return a 401
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data, {"detail": "X-Turn-Hook-Signature header required"}
        )

    def test_signature_valid(self):
        """
        If the HMAC signature is invalid, we should return a descriptive error
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url, data, format="json", HTTP_X_TURN_HOOK_SIGNATURE="foo"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {"detail": "Invalid hook signature"})


class CHWRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("chwregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "id_type": "dob",
                "id_number": "",
                "passport_country": "",
                "passport_number": "",
                "date_of_birth": "1990-02-03",
                "language": "nso",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = CHWRegistration.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(channelswitch.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(channelswitch.source, "WhatsApp")
        self.assertEqual(channelswitch.id_type, "dob")
        self.assertEqual(channelswitch.date_of_birth, datetime.date(1990, 2, 3))
        self.assertEqual(channelswitch.language, "nso")
        self.assertEqual(channelswitch.created_by, user.username)

    def test_chw_other_passport_origin(self):
        """
        Should create a new CHWRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "",
                "date_of_birth": "1990-02-03",
                "language": "nso",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = CHWRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")


class Covid19TriageViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("covid19triage-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch(
        "eventstore.models.HealthCheckUserProfile.update_post_screening_study_arms"
    )
    @mock.patch("eventstore.views.mark_turn_contact_healthcheck_complete")
    def test_successful_request(self, task, mock_update_post_screening_study_arms):
        """
        Should create a new Covid19Triage object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "msisdn": "27820001001",
                "source": "USSD",
                "province": "ZA-WC",
                "city": "cape town",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [covid19triage] = Covid19Triage.objects.all()
        self.assertEqual(covid19triage.msisdn, "+27820001001")
        self.assertEqual(covid19triage.source, "USSD")
        self.assertEqual(covid19triage.province, "ZA-WC")
        self.assertEqual(covid19triage.city, "cape town")
        self.assertEqual(covid19triage.age, Covid19Triage.AGE_18T40)
        self.assertEqual(covid19triage.fever, False)
        self.assertEqual(covid19triage.cough, False)
        self.assertEqual(covid19triage.sore_throat, False)
        self.assertEqual(covid19triage.difficulty_breathing, None)
        self.assertEqual(covid19triage.exposure, Covid19Triage.EXPOSURE_NO)
        self.assertEqual(covid19triage.tracing, True)
        self.assertEqual(covid19triage.gender, "")
        self.assertEqual(covid19triage.location, "")
        self.assertEqual(covid19triage.muscle_pain, None)
        self.assertEqual(covid19triage.smell, None)
        self.assertEqual(covid19triage.preexisting_condition, "")
        self.assertIsInstance(covid19triage.deduplication_id, str)
        self.assertNotEqual(covid19triage.deduplication_id, "")
        self.assertEqual(covid19triage.risk, Covid19Triage.RISK_LOW)
        self.assertEqual(covid19triage.created_by, user.username)
        task.delay.assert_called_once_with("+27820001001")

        mock_update_post_screening_study_arms.assert_called_with(
            Covid19Triage.RISK_LOW, "USSD"
        )

    @mock.patch(
        "eventstore.models.HealthCheckUserProfile.update_post_screening_study_arms"
    )
    def test_duplicate_request(self, mock_update_post_screening_study_arms):
        """
        Should create on the first request, and just return 200 on subsequent requests
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        data = {
            "deduplication_id": "testid",
            "msisdn": "27820001001",
            "source": "USSD",
            "province": "ZA-WC",
            "city": "cape town",
            "age": Covid19Triage.AGE_18T40,
            "fever": False,
            "cough": False,
            "sore_throat": False,
            "exposure": Covid19Triage.EXPOSURE_NO,
            "tracing": True,
            "risk": Covid19Triage.RISK_LOW,
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_update_post_screening_study_arms.assert_called_with(
            Covid19Triage.RISK_LOW, "USSD"
        )

    def test_invalid_location_request(self):
        """
        Should create a new Covid19Triage object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "msisdn": "+27820001001",
                "source": "USSD",
                "province": "ZA-WC",
                "city": "cape town",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
                "location": "invalid",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["location"], ["Invalid ISO6709 geographic coordinate"]
        )

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="view_covid19triage"))
        self.client.force_authenticate(user)

        triage_old = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        triage_new = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        Covid19Triage.objects.create(
            msisdn="+27820001002",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': triage_old.timestamp.isoformat(), 'msisdn': '+27820001001'})}"  # noqa
        )
        self.assertEqual(
            response.data["results"],
            [Covid19TriageSerializer(instance=triage_new).data],
        )
        [r] = response.data["results"]
        r.pop("id")
        r.pop("deduplication_id")
        r.pop("timestamp")
        r.pop("completed_timestamp")
        self.assertEqual(
            r,
            {
                "msisdn": "+27820001001",
                "source": "USSD",
                "province": "ZA-WC",
                "city": "Cape Town",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "difficulty_breathing": None,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
                "gender": "",
                "location": "",
                "muscle_pain": None,
                "smell": None,
                "preexisting_condition": "",
                "created_by": "",
                "data": {},
            },
        )

    @mock.patch(
        "eventstore.models.HealthCheckUserProfile.update_post_screening_study_arms"
    )
    def test_creates_user_profile(self, mock_update_post_screening_study_arms):
        """
        The user profile should be created when the triage is saved
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        self.client.post(
            self.url,
            {
                "msisdn": "27820001001",
                "source": "USSD",
                "province": "ZA-WC",
                "city": "cape town",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
            },
            format="json",
        )
        profile = HealthCheckUserProfile.objects.get(msisdn="+27820001001")
        self.assertEqual(profile.province, "ZA-WC")
        self.assertEqual(profile.city, "cape town")
        self.assertEqual(profile.age, Covid19Triage.AGE_18T40)

        mock_update_post_screening_study_arms.assert_called_with(
            Covid19Triage.RISK_LOW, "USSD"
        )

    def test_creates_dbe_user_profile(self):
        """
        If this is a DBE healthcheck from a parent profile, then a DBE user profile
        should be created
        """
        user = get_user_model().objects.create_user("whatsapp_dbe_healthcheck")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)
        result = self.client.post(
            self.url,
            {
                "msisdn": "27820001001",
                "source": "WhatsApp",
                "gender": Covid19Triage.GENDER_NOT_SAY,
                "province": "ZA-WC",
                "city": "cape town",
                "city_location": "",
                "location": "",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
                "preexisting_condition": Covid19Triage.EXPOSURE_NOT_SURE,
                "data": {
                    "profile": "parent",
                    "age": 23,
                    "name": "test name",
                    "school_name": "BERGVLIET HIGH SCHOOL",
                    "school_emis": "12345",
                    "obesity": False,
                    "diabetes": None,
                    "hypertension": True,
                    "cardio": False,
                },
            },
            format="json",
        )
        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        [profile] = DBEOnBehalfOfProfile.objects.filter(msisdn="+27820001001")
        self.assertEqual(profile.name, "test name")
        self.assertEqual(profile.age, 23)
        self.assertEqual(profile.gender, Covid19Triage.GENDER_NOT_SAY)
        self.assertEqual(profile.province, "ZA-WC")
        self.assertEqual(profile.city, "cape town")
        self.assertEqual(profile.city_location, "")
        self.assertEqual(profile.location, "")
        self.assertEqual(profile.school, "BERGVLIET HIGH SCHOOL")
        self.assertEqual(profile.school_emis, "12345")
        self.assertEqual(profile.preexisting_condition, Covid19Triage.EXPOSURE_NOT_SURE)
        self.assertEqual(profile.obesity, False)
        self.assertEqual(profile.diabetes, None)
        self.assertEqual(profile.hypertension, True)
        self.assertEqual(profile.cardio, False)


class Covid19TriageV2ViewSetTests(Covid19TriageViewSetTests):
    url = reverse("covid19triagev2-list")

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="view_covid19triage"))
        self.client.force_authenticate(user)

        triage_old = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        triage_new = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': triage_old.timestamp.isoformat()})}"
        )
        self.assertEqual(
            response.data["results"],
            [Covid19TriageV2Serializer(instance=triage_new).data],
        )
        [r] = response.data["results"]
        r.pop("id")
        r.pop("deduplication_id")
        r.pop("timestamp")
        r.pop("completed_timestamp")
        self.assertEqual(
            r,
            {
                "msisdn": "+27820001001",
                "first_name": None,
                "last_name": None,
                "source": "USSD",
                "province": "ZA-WC",
                "city": "Cape Town",
                "age": Covid19Triage.AGE_18T40,
                "date_of_birth": None,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "difficulty_breathing": None,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "confirmed_contact": None,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
                "gender": "",
                "location": "",
                "city_location": None,
                "muscle_pain": None,
                "smell": None,
                "preexisting_condition": "",
                "rooms_in_household": None,
                "persons_in_household": None,
                "created_by": "",
                "data": {},
            },
        )

    @mock.patch(
        "eventstore.models.HealthCheckUserProfile.update_post_screening_study_arms"
    )
    def test_returning_user(self, mock_update_post_screening_study_arms):
        """
        Should create a new Covid19Triage object in the database using information
        from the first entry in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        Covid19Triage.objects.create(
            msisdn="+27820001001",
            province="ZA-WC",
            city="cape town",
            fever=False,
            cough=False,
            sore_throat=False,
            tracing=True,
        )
        Covid19Triage.objects.create(
            msisdn="+27820001001",
            province="ZA-GT",
            city="sandton",
            fever=False,
            cough=False,
            sore_throat=False,
            tracing=True,
        )

        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "msisdn": "27820001001",
                "source": "USSD",
                "age": Covid19Triage.AGE_18T40,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        triage_id = response.data["id"]
        covid19triage = Covid19Triage.objects.get(id=triage_id)
        self.assertEqual(covid19triage.province, "ZA-WC")
        self.assertEqual(covid19triage.city, "cape town")

        mock_update_post_screening_study_arms.assert_called_with(
            Covid19Triage.RISK_LOW, "USSD"
        )


class Covid19TriageV3ViewSetTests(Covid19TriageViewSetTests):
    url = reverse("covid19triagev3-list")

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="view_covid19triage"))
        self.client.force_authenticate(user)

        triage_old = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
        )
        triage_new = Covid19Triage.objects.create(
            msisdn="+27820001001",
            source="USSD",
            province="ZA-WC",
            city="Cape Town",
            age=Covid19Triage.AGE_18T40,
            fever=False,
            cough=False,
            sore_throat=False,
            exposure=Covid19Triage.EXPOSURE_NO,
            tracing=True,
            risk=Covid19Triage.RISK_LOW,
            place_of_work=Covid19Triage.WORK_HEALTHCARE,
        )
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': triage_old.timestamp.isoformat()})}"
        )
        self.assertEqual(
            response.data["results"],
            [Covid19TriageV3Serializer(instance=triage_new).data],
        )
        [r] = response.data["results"]
        r.pop("id")
        r.pop("deduplication_id")
        r.pop("timestamp")
        r.pop("completed_timestamp")
        self.assertEqual(
            r,
            {
                "msisdn": "+27820001001",
                "first_name": None,
                "last_name": None,
                "source": "USSD",
                "province": "ZA-WC",
                "city": "Cape Town",
                "age": Covid19Triage.AGE_18T40,
                "date_of_birth": None,
                "fever": False,
                "cough": False,
                "sore_throat": False,
                "difficulty_breathing": None,
                "exposure": Covid19Triage.EXPOSURE_NO,
                "confirmed_contact": None,
                "tracing": True,
                "risk": Covid19Triage.RISK_LOW,
                "gender": "",
                "location": "",
                "city_location": None,
                "muscle_pain": None,
                "smell": None,
                "preexisting_condition": "",
                "rooms_in_household": None,
                "persons_in_household": None,
                "created_by": "",
                "data": {},
                "place_of_work": Covid19Triage.WORK_HEALTHCARE,
            },
        )


class Covid19TriageStartViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("covid19triagestart-list")
    add_codename = "add_covid19triagestart"
    view_codename = "view_covid19triagestart"

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename=self.add_codename))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new Covid19TriageStart object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename=self.add_codename))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url, {"msisdn": "27820001001", "source": "USSD *123#"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [start] = Covid19TriageStart.objects.all()
        self.assertEqual(start.msisdn, "+27820001001")
        self.assertEqual(start.source, "USSD *123#")
        self.assertEqual(start.created_by, user.username)

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename=self.view_codename))
        self.client.force_authenticate(user)

        start_old = Covid19TriageStart.objects.create(
            msisdn="+27820001001", source="USSD"
        )
        start_new = Covid19TriageStart.objects.create(
            msisdn="+27820001001", source="USSD"
        )
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': start_old.timestamp.isoformat()})}"
        )
        self.assertEqual(
            response.data["results"],
            [Covid19TriageStartSerializer(instance=start_new).data],
        )
        [r] = response.data["results"]
        r.pop("id")
        r.pop("timestamp")
        self.assertEqual(
            r, {"msisdn": "+27820001001", "source": "USSD", "created_by": ""}
        )


class HealthCheckUserProfileViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("healthcheckuserprofile-detail", args=("+27820001001",))

    def test_no_data(self):
        """
        Should return a 404 if no data
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="view_healthcheckuserprofile")
        )
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch(
        "eventstore.models.HealthCheckUserProfile.update_post_screening_study_arms"
    )
    def test_existing_healthchecks(self, mock_update_post_screening_study_arms):
        """
        If there's no profile, but existing healthchecks, then it should construct the
        profile from those healthchecks
        """
        Covid19Triage.objects.create(
            msisdn="+27820001001",
            first_name="testname",
            fever=False,
            cough=False,
            sore_throat=False,
            tracing=True,
        )
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="view_healthcheckuserprofile")
        )
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msisdn"], "+27820001001")
        self.assertEqual(response.data["first_name"], "testname")

        mock_update_post_screening_study_arms.assert_not_called()

    def test_existing_profile(self):
        """
        It should return the existing profile
        """
        HealthCheckUserProfile.objects.create(
            msisdn="+27820001001", first_name="testname"
        )
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="view_healthcheckuserprofile")
        )
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.maxDiff = None
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["msisdn"], "+27820001001")
        self.assertEqual(response.data["first_name"], "testname")


class CDUAddressUpdateViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("cduaddressupdate-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_cduaddressupdate")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new CDUAddressUpdate object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_cduaddressupdate")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "id_type": "dob",
                "id_number": "",
                "date_of_birth": "1990-02-03",
                "folder_number": "12345567",
                "district": "Cape Town",
                "municipality": "Cape Town East",
                "city": "Cape Town",
                "suburb": "Sea Point",
                "street_name": "High Level Road",
                "street_number": "197",
                "msisdn": "+278564546",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [cduAddressUpdate] = CDUAddressUpdate.objects.all()
        self.assertEqual(cduAddressUpdate.first_name, "Jane")
        self.assertEqual(cduAddressUpdate.last_name, "Smith")
        self.assertEqual(cduAddressUpdate.id_type, "dob")
        self.assertEqual(cduAddressUpdate.id_number, "")
        self.assertEqual(cduAddressUpdate.date_of_birth, datetime.date(1990, 2, 3))
        self.assertEqual(cduAddressUpdate.folder_number, "12345567")
        self.assertEqual(cduAddressUpdate.district, "Cape Town")
        self.assertEqual(cduAddressUpdate.municipality, "Cape Town East")
        self.assertEqual(cduAddressUpdate.city, "Cape Town")
        self.assertEqual(cduAddressUpdate.suburb, "Sea Point")
        self.assertEqual(cduAddressUpdate.street_name, "High Level Road")
        self.assertEqual(cduAddressUpdate.street_number, "197")
        self.assertEqual(cduAddressUpdate.msisdn, "+278564546")


class DBEOnBehalfOfProfileTests(APITestCase):
    url = reverse("dbeonbehalfofprofile-list")

    def create_profile(self, **kwargs):
        default = {
            "msisdn": "+27820001001",
            "age": 12,
            "gender": Covid19Triage.GENDER_MALE,
            "province": "ZA-WC",
            "city": "Cape Town",
            "school": "Bergvliet High School",
            "school_emis": "105310201",
            "preexisting_condition": Covid19Triage.EXPOSURE_NO,
        }
        default.update(kwargs)
        return DBEOnBehalfOfProfile.objects.create(**default)

    def test_authentication_required(self):
        """
        There must be an authenticated user to make the request
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_required(self):
        """
        The authenticated user must have permission to access the endpoint
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_no_filter(self):
        """
        Should return all profiles
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="view_dbeonbehalfofprofile")
        )
        self.client.force_authenticate(user)

        self.create_profile(msisdn="+27820001001")
        self.create_profile(msisdn="+27820001002")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)

    def test_get_msisdn_filter(self):
        """
        Should only return the profiles associated with that MSISDN
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="view_dbeonbehalfofprofile")
        )
        self.client.force_authenticate(user)

        self.create_profile(msisdn="+27820001001")
        self.create_profile(msisdn="+27820001001")
        self.create_profile(msisdn="+27820001002")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)


class AdaAssessmentNotificationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("adaassessmentnotification-list")

    def test_querystring_token_auth(self):
        """
        Auth should be done through a token in the querystring
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token = Token.objects.create(user=user)
        response = self.client.post(f"{self.url}?token={token.key}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validates_request_data(self):
        """
        Should return errors for invalid request data
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "id": ["This field is required."],
                "entry": ["This field is required."],
                "timestamp": ["This field is required."],
            },
        )

    def test_validates_patient_data(self):
        """
        Should return errors for invalid patient entry
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            {
                "id": "abc123",
                "entry": [{"resource": {"resourceType": "Patient"}}],
                "timestamp": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "entry": {
                    "0": {
                        "resource": {
                            "id": ["This field is required."],
                            "birthDate": ["This field is required."],
                        }
                    }
                }
            },
        )

    def test_validates_observation_data(self):
        """
        Should return errors for invalid observation entry
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            {
                "id": "abc123",
                "entry": [
                    {"resource": {"resourceType": "Observation", "valueBoolean": "a"}}
                ],
                "timestamp": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "entry": {
                    "0": {
                        "resource": {
                            "code": ["This field is required."],
                            "valueBoolean": ["Must be a valid boolean."],
                        }
                    }
                }
            },
        )

    def test_missing_patient_data(self):
        """
        Should return errors if there's no patient data in the entries
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            {"id": "abc123", "entry": [], "timestamp": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"entry": ["No patient entry found"]})

    def test_missing_observations(self):
        """
        Should return errors if required observations are missing
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            {
                "id": "abc123",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "abc123",
                            "birthDate": "1990-01-02",
                        }
                    },
                    {"resource": {"resourceType": "Condition"}},
                ],
                "timestamp": "2021-01-02T03:04:05Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            sorted(response.json()["entry"]),
            [
                "Missing observation cough",
                "Missing observation fever",
                "Missing observation sore throat",
            ],
        )

    def test_valid_data(self):
        """
        Should return errors if there's no patient data in the entries
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_covid19triage"))
        self.client.force_authenticate(user)

        response = self.client.post(
            self.url,
            {
                "id": "abc123",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "code": {"text": "cough"},
                            "valueBoolean": True,
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "code": {"text": "fever"},
                            "valueBoolean": False,
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "code": {"text": " Sore throat"},
                            "valueBoolean": False,
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "abc123",
                            "birthDate": "1990-01-02",
                        }
                    },
                    {"resource": {"resourceType": "Condition"}},
                ],
                "timestamp": "2021-01-02T03:04:05Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.json(),
            {
                "id": "abc123",
                "username": "test",
                "patient_id": "abc123",
                "patient_dob": "1990-01-02",
                "observations": {"cough": True, "fever": False, "sore throat": False},
                "timestamp": "2021-01-02T03:04:05Z",
            },
        )
