import logging
from unittest import mock
from urllib.parse import urljoin

import requests.exceptions
from django.conf import settings
from django.test import TestCase

from nluclassifier.tasks import process_feedback_for_labeling

logger = logging.getLogger(__name__)


# fmt: off
class NLUClassifierTaskTests(TestCase):
    """
    Tests for the Celery task that handles NLU classification
    and Turn message labeling. The tests verify API calls and
    ensure RequestExceptions are re-raised for Celery's autoretry
    """

    def setUp(self):
        self.settings = settings

        self.message_id = "12345"
        self.inbound_message = "I am not happy with your service."

        self.expected_intent = "COMPLAINT"

    def test_successful_classification_and_labeling(self):
        """
        Tests the end-to-end flow where NLU classifies the message and
        Turn successfully applies the label
        """
        nlu_success_mock = mock.Mock(status_code=200)
        nlu_success_mock.json.return_value = {
            "intent": self.expected_intent,
            "model_version": "2025-09-29-v1",
            "parent_label": "FEEDBACK",
            "probability": 0.3805,
            "review_status": "NEEDS_REVIEW",
        }
        nlu_success_mock.raise_for_status.return_value = None

        turn_success_mock = mock.Mock(status_code=202)
        turn_success_mock.raise_for_status.return_value = None

        with (
            mock.patch("requests.get") as mock_get,
            mock.patch("requests.post") as mock_post,
        ):

            mock_get.return_value = nlu_success_mock
            mock_post.return_value = turn_success_mock

            result = process_feedback_for_labeling(
                self.message_id, self.inbound_message
            )

            expected_nlu_endpoint = urljoin(
                self.settings.INTENT_CLASSIFIER_URL, "/nlu/feedback/"
            )

            self.assertEqual(mock_get.call_count, 1)
            nlu_call_args = mock_get.call_args
            self.assertEqual(nlu_call_args[0][0], expected_nlu_endpoint)
            self.assertEqual(
                nlu_call_args[1]["auth"],
                (
                    self.settings.INTENT_CLASSIFIER_USER,
                    self.settings.INTENT_CLASSIFIER_PASS,
                ),
            )
            self.assertEqual(
                nlu_call_args[1]["params"]["question"], self.inbound_message
            )

            self.assertEqual(mock_post.call_count, 1)
            turn_call_args = mock_post.call_args
            self.assertIn(
                f"messages/{self.message_id}/labels",
                turn_call_args[0][0]
                )
            self.assertEqual(
                turn_call_args[1]["headers"]["Authorization"],
                f"Bearer {self.settings.TURN_TOKEN}",
            )

            turn_payload = turn_call_args[1]["json"]
            self.assertEqual(
                turn_payload["labels"],
                [self.expected_intent.lower()]
                )

            self.assertTrue(result is None)

    def test_nlu_api_failure_raises_exception_for_celery_retry(self):
        """
        Tests that if the NLU API returns a failure,
        a RequestException is raised
        """
        nlu_fail_mock = mock.Mock(status_code=404)
        error = requests.exceptions.HTTPError("404 Not Found")
        nlu_fail_mock.raise_for_status.side_effect = error

        with (
            mock.patch("requests.get") as mock_get,
            mock.patch("requests.post") as mock_post,
            self.assertLogs(
                "nluclassifier.tasks", level="WARNING") as log_context,
        ):

            mock_get.return_value = nlu_fail_mock

            with self.assertRaises(requests.exceptions.HTTPError):
                process_feedback_for_labeling(
                    self.message_id, self.inbound_message)

            self.assertEqual(mock_get.call_count, 1)

            self.assertEqual(mock_post.call_count, 0)

            self.assertTrue(
                any(
                    "NLU service failed for message" in output
                    for output in log_context.output
                )
            )

    def test_no_label_applied_on_unhandled_intent(self):
        """
        Tests that if NLU returns an intent that is not
        'compliment' or 'complaint'.
        No Turn API call is made.
        """
        nlu_success_mock = mock.Mock(status_code=200)

        nlu_success_mock.json.return_value = {
            "intent": "None",
            "model_version": "2025-09-29-v1",
            "parent_label": "SENSITIVE_EXIT",
            "probability": 0.3357,
            "review_status": "NEEDS_REVIEW",
        }
        nlu_success_mock.raise_for_status.return_value = None

        with (
            mock.patch("requests.get") as mock_get,
            mock.patch("requests.post") as mock_post,
            self.assertLogs(
                "nluclassifier.tasks", level="INFO") as log_context,
        ):

            mock_get.return_value = nlu_success_mock

            result = process_feedback_for_labeling(
                self.message_id, self.inbound_message
            )

            self.assertEqual(mock_get.call_count, 1)

            self.assertEqual(mock_post.call_count, 0)

            self.assertTrue(
                any("No Turn label applied" in output
                    for output in log_context.output)
            )
            self.assertTrue(result is None)
