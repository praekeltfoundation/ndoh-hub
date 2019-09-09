from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from eventstore.models import BabySwitch, OptOut


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
