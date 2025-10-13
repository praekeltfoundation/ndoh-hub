from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


# fmt: off
class NLUWebhookTests(APITestCase):
    def setUp(self):
        self.url = reverse("label_feedback")

        self.username = "testuser"
        self.password = "password"
        self.user = User.objects.create_user(
            self.username, password=self.password)

        self.message_id = "turn-messageid-123"
        self.inbound_message = "I love this service, it is great."
        self.valid_data = {
            "message_id": self.message_id,
            "inbound_message": self.inbound_message,
        }

    def test_unauthenticated_request_is_unauthorized(self):
        """
        An unauthenticated request should be rejected with 401 Unauthorized
        """
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn(
            "Authentication credentials were not provided.",
            response.json().get("detail", ""),
        )

    @patch("nluclassifier.views.process_feedback_for_labeling.delay")
    def test_auth_valid_params_task_202(
        self, mock_delay
    ):
        """
        An authenticated POST request with required body parameters
        should queue the Celery task and return 202
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url, self.valid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        mock_delay.assert_called_once_with(
            self.message_id, self.inbound_message)

        self.assertEqual(
            response.json()["status"],
            "Feedback labeling process initiated successfully.",
        )

    @patch("nluclassifier.views.process_feedback_for_labeling.delay")
    def test_authenticated_request_missing_required_params_returns_400(
        self, mock_delay
    ):
        """
        An authenticated request missing required body parameters should return
        400 Bad Request and not queue the task.
        """
        self.client.force_authenticate(user=self.user)

        response_missing_id = self.client.post(
            self.url, {"inbound_message": self.inbound_message}, format="json"
        )
        self.assertEqual(
            response_missing_id.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Missing 'message_id' or 'inbound_message' parameter",
            response_missing_id.json()["error"],
        )

        response_missing_msg = self.client.post(
            self.url, {"message_id": self.message_id}, format="json"
        )
        self.assertEqual(
            response_missing_msg.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Missing 'message_id' or 'inbound_message' parameter",
            response_missing_msg.json()["error"],
        )

        mock_delay.assert_not_called()

    @patch("nluclassifier.views.process_feedback_for_labeling.delay")
    def test_method_not_allowed(self, mock_delay):
        """
        Check that Only POST method is allowed otherwise 405 is returned
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url, data=self.valid_data)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        mock_delay.assert_not_called()
