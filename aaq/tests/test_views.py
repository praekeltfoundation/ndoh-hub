import json
import responses
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import FakeAaqCoreApi


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
    def test_get_first_page_view_no_words(self):
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
            "message": "",
            "body": {},
            "feedback_secret_key": "xxx",
            "inbound_secret_key": "yyy",
            "inbound_id": "iii",
        }

    @responses.activate
    def test_get_first_page_view_blank(self):
        """
        Check that we get an error message if a blank question is submitted
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
        # test string value, bad question, empty str, emoji, int

        response = self.client.post(
            self.url, data=payload, content_type="application/json"
        )

        assert response.json() == {"question": ["This field may not be blank."]}
