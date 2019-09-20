from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from eventstore.models import BabySwitch, ChannelSwitch, OptOut, PublicRegistration


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
        self.assertEqual(optout.created_by, user)


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
        self.assertEqual(babyswitch.created_by, user)


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
        self.assertEqual(channelswitch.created_by, user)


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
        self.assertEqual(channelswitch.created_by, user)
