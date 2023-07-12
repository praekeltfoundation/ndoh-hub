import json

import responses
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import FakeAaqCoreApi, FakeAaqUdApi, FakeTask


class GetFirstPageViewTests(APITestCase):
    url = reverse("aaq-get-first-page")

    def test_unauthenticated(self):
        """
        Unauthenticated users cannot access the API
        """
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # TODO: Test how we handle errors from aaq core?

    @responses.activate
    def test_get_first_page_view(self):
        """
        Check that we get 5 faqs returned with 1st page of inbound check
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeCoreApi = FakeAaqCoreApi()
        responses.add_callback(
            responses.POST,
            "http://aaqcore/inbound/check",
            callback=fakeCoreApi.post_inbound_check,
            content_type="application/json",
        )

        payload = json.dumps({"question": "I am pregnant and also out of breath"})
        # test string value, bad question, empty str, emoji, int

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )
        assert response.json() == {
            "message": "*1* - short of breath\n*2* - Fainting in pregnancy\n"
            "*3* - Bleeding in pregnancy\n*4* - Sleep in pregnancy\n*5* - "
            "Breast pain",
            "body": {
                "1": {"text": "*Yes, pregnancy can affect your breathing", "id": "21"},
                "2": {
                    "text": "*Fainting could mean anemia – visit the clinic to "
                    "find out",
                    "id": "26",
                },
                "3": {
                    "text": "*Bleeding during pregnancy*\r\n \r\n*Early " "pregnancy",
                    "id": "114",
                },
                "4": {
                    "text": "*Get good sleep during pregnancy*\r\n\r\nGood "
                    "sleep is good",
                    "id": "111",
                },
                "5": {
                    "text": "*Sometimes breast pain needs to be checked at "
                    "the clinic",
                    "id": "150",
                },
            },
            "next_page_url": "/inbound/iii/ppp?inbound_secret_key=zzz",
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }

    @responses.activate
    def test_get_first_page_view_gibberish_input(self):
        """
        Check that we get a response with an empty list in the top_responses part
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeCoreApi = FakeAaqCoreApi()
        responses.add_callback(
            responses.POST,
            "http://aaqcore/inbound/check",
            callback=fakeCoreApi.post_inbound_check_return_empty,
            content_type="application/json",
        )

        payload = json.dumps({"question": "a"})
        # test string value, bad question, empty str, emoji, int

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )

        assert response.json() == {
            "message": "Gibberish Detected",
            "body": {},
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }

    @responses.activate
    def test_get_first_page_view_non_text(self):
        """
        Check that we get an error message if a blank question is submitted
        This happens when a voicenote or document is sent, or if an image is
        sent without a text caption
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeCoreApi = FakeAaqCoreApi()
        responses.add_callback(
            responses.POST,
            "http://aaqcore/inbound/check",
            callback=fakeCoreApi.post_inbound_check_return_empty,
            content_type="application/json",
        )

        payload = json.dumps({"question": ""})

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )

        assert response.json() == {"message": "Non-text Input Detected"}


class AddFeedbackViewTests(APITestCase):
    url = reverse("aaq-add-feedback")

    @responses.activate
    def test_faq_feedback_view(self):
        """Test that we can submit feedback on an FAQ"""
        data = {
            "feedback_secret_key": "dummy_secret",
            "inbound_id": "dummy_inbound_id",
            "feedback": {
                "feedback_type": "negative",
                "faq_id": "dummy_faq_id",
            },
        }
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeTask = FakeTask()
        responses.add_callback(
            responses.PUT,
            "http://aaqcore/inbound/feedback",
            callback=fakeTask.call_add_feedback_task,
            content_type="application/json",
        )

        payload = json.dumps(data)
        response = self.client.put(
            self.url, data=payload, content_type="application/json"
        )

        assert response.status_code == 202

    @responses.activate
    def test_page_feedback_view(self):
        """Test that we can submit feedback on an Page"""
        data = {
            "feedback_secret_key": "dummy_secret",
            "inbound_id": "dummy_inbound_id",
            "feedback": {
                "feedback_type": "positive",
                "page_number": "dummy_page_number",
            },
        }
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeTask = FakeTask()
        responses.add_callback(
            responses.PUT,
            "http://aaqcore/inbound/feedback",
            callback=fakeTask.call_add_feedback_task,
            content_type="application/json",
        )

        payload = json.dumps(data)
        response = self.client.put(
            self.url, data=payload, content_type="application/json"
        )

        assert response.status_code == 202

    def test_page_invalid_feedback_view(self):
        """Test that we can submit feedback on an Page"""
        data = {
            "feedback_secret_key": "dummy_secret",
            "inbound_id": "dummy_inbound_id",
            "feedback": {
                "feedback_type": "positive",
            },
        }
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        payload = json.dumps(data)
        response = self.client.put(
            self.url, data=payload, content_type="application/json"
        )

        assert response.status_code == 400
        assert response.json() == {
            "non_field_errors": [
                "At least one of faq_id or page_number must be supplied."
            ]
        }


class CheckUrgencyViewTests(APITestCase):
    url = reverse("aaq-check-urgency")

    @responses.activate
    def test_urgent(self):
        """
        Test that we can get an urgency score of 1.0
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeAaqUdApi = FakeAaqUdApi()
        responses.add_callback(
            responses.POST,
            "http://aaqud/inbound/check",
            callback=fakeAaqUdApi.post_inbound_check_return_one,
            content_type="application/json",
        )

        payload = json.dumps({"question": "I am pregnant and out of breath"})
        # test string value, bad question, empty str, emoji, int

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )

        assert response.json() == {"urgency_score": 1.0}

    @responses.activate
    def test_not_urgent(self):
        """
        Test that we can get an urgency score of 1.0
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeAaqUdApi = FakeAaqUdApi()
        responses.add_callback(
            responses.POST,
            "http://aaqud/inbound/check",
            callback=fakeAaqUdApi.post_inbound_check_return_zero,
            content_type="application/json",
        )

        payload = json.dumps({"question": "I am fine"})
        # test string value, bad question, empty str, emoji, int

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )

        assert response.json() == {"urgency_score": 0.0}
