import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mqr.models import MqrStrata
from mqr.utils import get_next_send_date
from mqr import utils


def override_get_today():
    return datetime.datetime.strptime("20220301", "%Y%m%d").date()


class NextMessageViewTests(APITestCase):
    url = reverse("mqr-nextmessage")

    def setUp(self):
        utils.get_today = override_get_today

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

        next_date = str(utils.get_next_send_date())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "message": "Test Message 1",
                "is_template": False,
                "next_send_date": next_date,
                "tag": "BCM_week_PRE19",
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


class StrataRandomization(APITestCase):
    url = reverse("mqr_randomstrataarm")

    def test_random_arm_unauthorized_user(self):
        """
        unauthorized user access denied
        Returns: status code 401

        """

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_random_arm(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        MqrStrata.objects.create(
            province="EC",
            weeks_pregnant_bucket="21-25",
            age_bucket="31+",
            next_index=3,
            order="RCM_SMS,RCM_BCM,RCM,ARM,BCM",
        )

        response = MqrStrata.objects.get(
            province="EC", weeks_pregnant_bucket="21-25", age_bucket="31+"
        )

        self.assertIsNotNone(response)
        self.assertEqual(response.province, "EC")

    def test_get_random_starta_arm(self):
        """
        Check the next arm from the existing data
        Returns: string response

        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        MqrStrata.objects.create(
            province="MP",
            weeks_pregnant_bucket="28-30",
            age_bucket="31+",
            next_index=1,
            order="ARM,RCM_BCM,RCM,RCM_SMS,BCM",
        )

        get_arm = MqrStrata.objects.get(
            province="MP", weeks_pregnant_bucket="28-30", age_bucket="31+"
        )

        response = self.client.post(
            self.url,
            data={
                "province": "MP",
                "weeks_pregnant_bucket": "28-30",
                "age_bucket": "31+",
            },
            format="json",
        )

        splitted_arms = get_arm.order.split(",")

        self.assertNotEqual(splitted_arms[0], "RCM_BCM")
        self.assertEqual(splitted_arms[1], "RCM_BCM")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_out_of_index_arm(self):
        """
        Test for out of index to delete the order after maximum arm
        """

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        strata = MqrStrata.objects.create(
            province="FS",
            weeks_pregnant_bucket="26-30",
            age_bucket="31+",
            next_index=4,
            order="ARM,RCM,RCM_SMS,BCM,RCM_BCM",
        )

        # This api call will delete the existing arm
        self.client.post(
            self.url,
            data={
                "province": "FS",
                "weeks_pregnant_bucket": "26-30",
                "age_bucket": "31+",
            },
            format="json",
        )

        # New arm will be created
        self.client.post(
            self.url,
            data={
                "province": "FS",
                "weeks_pregnant_bucket": "26-30",
                "age_bucket": "31+",
            },
            format="json",
        )

        get_resp = MqrStrata.objects.get(
            province="FS", weeks_pregnant_bucket="26-30", age_bucket="31+"
        )

        self.assertEqual(get_resp.next_index, 1)
        self.assertNotEqual(strata.id, get_resp.id)
        self.assertNotEqual(get_resp.order, "ARM,RCM,RCM_SMS,BCM,RCM_BCM")
