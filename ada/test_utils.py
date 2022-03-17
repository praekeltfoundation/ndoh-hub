from unittest import TestCase, mock
from unittest.mock import patch

import responses

from ada import utils


class TestStartAssessment(TestCase):
    get_rp_payload = {
        "value": "",
        "cardType": "",
        "step": "",
        "optionId": "",
        "path": "",
    }
    get_response = {
        "cardType": "TEXT",
        "title": {"en-GB": "Foobar en-GB text", "de-DE": "Foobar de-DE Text"},
        "description": {"en-GB": "Foobar en-GB text", "de-DE": "Foobar de-DE Text"},
        "options": [
            {
                "intent": "string",
                "optionId": 0,
                "text": {"en-GB": "Foobar en-GB text", "de-DE": "Foobar de-DE Text"},
                "additional": {},
            }
        ],
        "cardAttributes": {
            "format": "integer",
            "maximum": 0,
            "minimum": 0,
            "maxLength": 0,
            "minLength": 0,
            "pattern": "string",
        },
        "_links": {
            "next": {"href": "/assessments/assessment-id/dialog/next", "method": "GET"},
            "abort": {
                "href": "/assessments/assessment-id/dialog/abort",
                "method": "GET",
            },
        },
    }
    post_response = {
        "id": "assessment-id",
        "location": "/assessments/assessment-id",
        "_links": {
            "startAssessment": {
                "href": "/assessments/assessment-id/dialog",
                "method": "GET",
            }
        },
    }

    @patch("ada.utils.get_from_ada", return_value=get_response)
    @patch("ada.utils.post_to_ada_start_assessment", return_value=post_response)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_start_assessment(
        self, mock_get_rp_payload, mock_post_response, mock_get_response
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {})

        # my_mock_response = mock.Mock(status_code=200)
        # my_mock_response.json.return_value = request_to_ada
        # mock_post_to_ada.return_value = my_mock_response

        # response = utils.post_to_ada(request_to_ada)
        # self.assertEqual(response.status_code, 200)

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": "",
                "message": "Foobar en-GB text\n\nEnter *back* to go to the previous question or *abort* to end the assessment",
                "step": "",
                "optionId": 0,
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "TEXT",
            },
            response,
        )


class TestMultipleChoiceMessage(TestCase):
    get_rp_payload = {
        "path": "/assessments/assessment-id/dialog/next",
        "optionId": 0,
        "cardType": "TEXT",
        "step": 3,
        "value": "1",
    }
    get_from_ada = {
        "step": 4,
        "cardType": "CHOICE",
        "title": {"en-GB": "Enter Symptoms", "de-DE": "some de-DE Text"},
        "description": {"en-GB": "What is the issue?", "de-DE": "some de-DE Text"},
        "options": [
            {"optionId": 0, "value": "Abdominal pain"},
            {"optionId": 1, "value": "Headache"},
            {"optionId": 2, "value": "None of these"},
        ],
        "_links": {
            "next": {
                "href": "/assessments/assessment-id/dialog/next",
                "method": "POST",
            },
            "abort": {
                "href": "/assessments/assessment-id/dialog/abort",
                "method": "GET",
            },
        },
    }
    # @patch("ada.utils.get_path", return_value="hello")
    @patch("ada.utils.post_to_ada", return_value=get_from_ada)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_submit_and_get_next_question(self, mock_get_rp_payload, mock_post_to_ada):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 3})

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": 3,
                "message": "What is the issue?\n\nAbdominal pain\nHeadache\nNone of these\n\nChoose the option that matches your answer. Eg, 1 for Abdominal pain\n\nEnter *back* to go to the previous question or *abort* to end the assessment",
                "step": 4,
                "optionId": 0,
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "CHOICE",
            },
            response,
        )


class TestPreviousMessage(TestCase):
    get_rp_payload = {
        "path": "/assessments/assessment-id/dialog/next",
        "optionId": 8,
        "cardType": "TEXT",
        "step": 5,
        "value": "back",
    }
    get_from_ada = {
        "step": 4,
        "cardType": "INPUT",
        "title": {"en-GB": "Enter Symptoms", "de-DE": "some de-DE Text"},
        "description": {
            "en-GB": "Please type in the symptom that is troubling you, only one symptom at a time.",
            "de-DE": "some de-DE Text",
        },
        "options": [
            {
                "intent": "TEXT",
                "optionId": 8,
                "value": "",
                "additional": {"format": "string", "minLength": 1, "maxLength": 100},
            }
        ],
        "_links": {
            "next": {
                "href": "/assessments/assessment-id/dialog/next",
                "method": "POST",
            },
            "abort": {
                "href": "/assessments/assessment-id/dialog/abort",
                "method": "GET",
            },
        },
    }

    @patch("ada.utils.previous_question", return_value=get_from_ada)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_submit_and_get_previous_question(
        self, mock_get_rp_payload, mock_post_to_ada
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 5})

        # my_mock_response = mock.Mock(status_code=200)
        # my_mock_response.json.return_value = request_to_ada
        # mock_post_to_ada.return_value = my_mock_response

        # response = utils.post_to_ada(request_to_ada)
        # self.assertEqual(response.status_code, 200)

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": "",
                "message": "Please type in the symptom that is troubling you, only one symptom at a time.\n\nEnter *back* to go to the previous question or *abort* to end the assessment",
                "step": 4,
                "optionId": 8,
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "INPUT",
            },
            response,
        )


class TestReturnReport(TestCase):
    get_rp_payload = {
        "path": "/assessments/assessment-id/dialog/next",
        "optionId": 0,
        "cardType": "TEXT",
        "step": 15,
        "value": "1",
    }
    get_from_ada = {
        "cardType": "TEXT",
        "title": {"en-GB": "End of assessment", "de-DE": "Foobar de-DE Text"},
        "description": {"en-GB": "Assessment complete", "de-DE": "Foobar de-DE Text"},
        "options": [
            {
                "intent": "string",
                "optionId": 0,
                "text": {"en-GB": "Assessment complete", "de-DE": "Foobar de-DE Text"},
                "additional": {},
            }
        ],
        "cardAttributes": {
            "format": "integer",
            "maximum": 0,
            "minimum": 0,
            "maxLength": 0,
            "minLength": 0,
            "pattern": "string",
        },
        "_links": {
            "next": {"href": "/assessments/assessment-id/dialog/next", "method": "GET"},
            "abort": {
                "href": "/assessments/assessment-id/dialog/abort",
                "method": "GET",
            },
            "report": {"href": "/reports/assessment-id", "method": "GET"},
        },
    }
    report_reponse = {"pdf sent"}

    @patch("ada.utils.get_report", return_value=report_reponse)
    @patch("ada.utils.post_to_ada", return_value=get_from_ada)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_start_assessment(
        self, mock_get_rp_payload, mock_post_response, mock_get_report
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 15})

        # my_mock_response = mock.Mock(status_code=200)
        # my_mock_response.json.return_value = request_to_ada
        # mock_post_to_ada.return_value = my_mock_response

        # response = utils.post_to_ada(request_to_ada)
        # self.assertEqual(response.status_code, 200)

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(response, {"pdf sent"}, response)
