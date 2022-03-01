from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mqr.models import MqrStrata


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

        response = self.client.post(
            self.url,
            data={"province": "EC", "weeks_pregnant": "30+", "age": 23},
            format="json",
        )

        self.assertEqual(type(response.data), str)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_random_starta_arm(self):
        """
        Check the next arm from the existing data
        Returns: string response

        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        MqrStrata.objects.create(
            province="MP",
            weeks_pregnant="28-30",
            age=25,
            next_index=1,
            order="ARM,RCM_BCM,RCM,RCM_SMS,BCM",
        )

        get_arm = MqrStrata.objects.get(province="MP", weeks_pregnant="28-30", age="25")

        response = self.client.post(
            self.url,
            data={"province": "MP", "weeks_pregnant": "28-30", "age": 25},
            format="json",
        )

        splitted_arms = get_arm.order.split(",")

        self.assertNotEqual(splitted_arms[0], response.data)
        self.assertEqual(splitted_arms[2], response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
