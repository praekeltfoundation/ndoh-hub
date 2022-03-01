from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from mqr.utils import get_next_send_date


class NextMessageViewTests(APITestCase):
    url = reverse("mqr-nextmessage")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "arm": ["This field is required."],
                "edd_or_dob_date": ["This field is required."],
                "subscription_type": ["This field is required."],
            },
        )

    @patch("mqr.views.get_message_details")
    def test_next_message(self, mock_get_message_details):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_message_details.return_value = {
            "is_template": False,
            "message": "Test Message 1",
        }

        response = self.client.post(
            self.url,
            {"arm": "BCM", "edd_or_dob_date": "2022-07-12", "subscription_type": "PRE"},
        )

        next_date = str(get_next_send_date())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "message": "Test Message 1",
                "is_template": False,
                "next_send_date": next_date,
                "tag": "BCM_week_PRE19"
            },
        )

    @patch("mqr.views.get_message_details")
    def test_next_message_error(self, mock_get_message_details):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_message_details.return_value = {"error": "no message found"}

        response = self.client.post(
            self.url,
            {"arm": "BCM", "edd_or_dob_date": "2022-07-12", "subscription_type": "PRE"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"error": "no message found"},
        )


class FaqViewTests(APITestCase):
    url = reverse("mqr-faq")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "tag": ["This field is required."],
                "faq_number": ["This field is required."],
            },
        )

    @patch("mqr.views.get_message_details")
    def test_faq_message(self, mock_get_message_details):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_message_details.return_value = {
            "is_template": False,
            "message": "Test Message 1",
        }

        response = self.client.post(
            self.url,
            {"tag": "BCM_week_pre22", "faq_number": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "message": "Test Message 1",
                "is_template": False,
            },
        )

        mock_get_message_details.assert_called_with("BCM_week_pre22_faq1")
