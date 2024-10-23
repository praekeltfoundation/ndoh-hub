import json

import responses
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from ..utils import check_urgency_v2, search
from .helpers import FakeAaqApi, FakeAaqUdV2Api


class SearchFunctionTest(APITestCase):

    @responses.activate
    def test_search_function(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        fakeAaqApi = FakeAaqApi()
        responses.add_callback(
            responses.POST,
            "http://aaq_v2/api/search",
            callback=fakeAaqApi.post_search,
            content_type="application/json",
        )

        fakeAaqUdV2Api = FakeAaqUdV2Api()
        responses.add_callback(
            responses.POST,
            "http://aaq_v2/api/urgency-detect",
            callback=fakeAaqUdV2Api.post_urgency_detect_return_true,
            content_type="application/json",
        )

        query_text = "test query"
        generate_llm_response = False
        query_metadata = {}

        payload = {
            "generate_llm_response": generate_llm_response,
            "query_metadata": query_metadata,
            "query_text": query_text,
        }

        response = search(query_text, generate_llm_response, query_metadata)

        search_request = responses.calls[0]

        self.assertIn("message", response)
        self.assertIn("body", response)
        self.assertIn("feedback_secret_key", response)
        self.assertIn("query_id", response)
        self.assertEqual(response["query_id"], 1)
        self.assertEqual(json.loads(search_request.request.body), payload)
        self.assertIn("Bearer", search_request.request.headers["Authorization"])
        assert response == {
            "message": "*1* - Example content title\n"
            "*2* - Another example content title",
            "body": {
                1: {"text": "Example content text", "id": 23},
                2: {"text": "Another example content text", "id": 12},
            },
            "feedback_secret_key": "secret-key-12345-abcde",
            "query_id": 1,
            "details": {
                "1": {"distance": 0.1, "urgency_rule": "Blurry vision and dizziness"},
                "2": {"distance": 0.2, "urgency_rule": "Nausea that lasts for 3 days"},
            },
            "is_urgent": True,
            "matched_rules": [
                "Blurry vision and dizziness",
                "Nausea that lasts for 3 days",
            ],
        }

    @responses.activate
    def test_urgency_check(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        fakeAaqUdV2Api = FakeAaqUdV2Api()
        responses.add_callback(
            responses.POST,
            "http://aaq_v2/api/urgency-detect",
            callback=fakeAaqUdV2Api.post_urgency_detect_return_true,
            content_type="application/json",
        )

        message_text = "Test message"

        response = check_urgency_v2(message_text)

        [request] = responses.calls

        self.assertIn("details", response)
        self.assertIn("is_urgent", response)
        self.assertIn("matched_rules", response)
        self.assertEqual(
            json.loads(request.request.body), {"message_text": message_text}
        )
        self.assertIn("Bearer", request.request.headers["Authorization"])

        assert response == {
            "details": {
                "1": {"distance": 0.1, "urgency_rule": "Blurry vision and dizziness"},
                "2": {"distance": 0.2, "urgency_rule": "Nausea that lasts for 3 days"},
            },
            "is_urgent": True,
            "matched_rules": [
                "Blurry vision and dizziness",
                "Nausea that lasts for 3 days",
            ],
        }

    @responses.activate
    def test_search_gibberish(self):
        """
        Check that we get a response with an empty list in the search results part
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        fakeAaqApi = FakeAaqApi()
        responses.add_callback(
            responses.POST,
            "http://aaq_v2/api/search",
            callback=fakeAaqApi.post_search_return_empty,
            content_type="application/json",
        )

        query_text = "jgghkjfhtfftf"
        generate_llm_response = False
        query_metadata = {}
        response = search(query_text, generate_llm_response, query_metadata)

        search_request = responses.calls[0]

        assert search_request.response.status_code == 400
        assert response == {
            "message": "Gibberish Detected",
        }
