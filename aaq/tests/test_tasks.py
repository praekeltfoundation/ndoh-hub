import json

import responses
from django.test import TestCase

from aaq.tasks import send_feedback_task


class AddFeedbackTaskTest(TestCase):
    @responses.activate
    def test_add_feedback_faq_task(self):
        data = {
            "feedback_secret_key": "dummy_secret",
            "inbound_id": "dummy_inbound_id",
            "feedback": {
                "feedback_type": "dummy_feedback_type",
                "faq_id": "dummy_faq_id",
            },
        }

        responses.add(
            responses.PUT,
            "http://aaqcore/inbound/feedback",
            json={},
            status=201,
        )
        kwargs = {}
        kwargs["faq_id"] = "dummy_faq_id"
        send_feedback_task.delay(
            "dummy_secret", "dummy_inbound_id", "dummy_feedback_type", **kwargs
        )

        [request] = responses.calls

        self.assertEqual(request.request.url, "http://aaqcore/inbound/feedback")
        self.assertEqual(json.loads(request.request.body), data)

    @responses.activate
    def test_add_feedback_page_task(self):
        data = {
            "feedback_secret_key": "dummy_secret",
            "inbound_id": "dummy_inbound_id",
            "feedback": {
                "feedback_type": "dummy_feedback_type",
                "page_number": "dummy_page_number",
            },
        }

        responses.add(
            responses.PUT,
            "http://aaqcore/inbound/feedback",
            json={},
            status=201,
        )
        kwargs = {}
        kwargs["page_number"] = "dummy_page_number"
        send_feedback_task.delay(
            "dummy_secret", "dummy_inbound_id", "dummy_feedback_type", **kwargs
        )

        [request] = responses.calls

        self.assertEqual(request.request.url, "http://aaqcore/inbound/feedback")
        self.assertEqual(json.loads(request.request.body), data)
