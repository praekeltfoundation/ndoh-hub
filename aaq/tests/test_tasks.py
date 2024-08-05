import json

import responses
from django.test import TestCase

from aaq.tasks import send_feedback_task, send_feedback_task_v2


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


class ContentFeedbackTaskTest(TestCase):
    @responses.activate
    def test_content_feedback_task(self):
        data = {
            "feedback_secret_key": "secret 12345",
            "query_id": 1,
            "content_id": 1,
            "feedback_sentiment": "negative",
            "feedback_text": "Not helpful",
        }

        responses.add(
            responses.POST,
            "http://aaq_v2/content-feedback",
            json={},
            status=200,
        )

        kwargs = {}
        kwargs["feedback_sentiment"] = "negative"
        kwargs["feedback_text"] = "Not helpful"
        send_feedback_task_v2.delay(
            "secret 12345",
            1,
            1,
            **kwargs,
        )

        [request] = responses.calls

        self.assertEqual(request.request.url, "http://aaq_v2/content-feedback")
        self.assertEqual(json.loads(request.request.body), data)
