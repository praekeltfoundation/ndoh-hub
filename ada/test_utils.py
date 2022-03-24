from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from ada import utils

from .models import AdaAssessment


class TestStartAssessment(TestCase):
    get_rp_payload = {
        "contact_uuid": "49548747-48888043",
        "choices": "",
        "value": "",
        "cardType": "",
        "step": "",
        "optionId": "",
        "path": "",
        "title": "",
    }
    next_dialog_response = {
        "cardType": "TEXT",
        "step": 1,
        "title": {"en-US": "WELCOME TO ADA"},
        "description": {
            "en-US": (
                "Welcome to the MomConnect Symptom Checker in "
                "partnership with Ada. Let's start with some questions "
                "about the symptoms. Then, we will help you "
                "decide what to do next."
            )
        },
        "label": {"en-US": "Continue"},
        "_links": {
            "self": {
                "method": "GET",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3",
            },
            "next": {
                "method": "POST",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
            },
            "previous": {
                "method": "POST",
                "href": (
                    "/assessments/"
                    "654f856d-c602-4347-8713-8f8196d66be3/dialog/previous"
                ),
            },
            "abort": {
                "method": "PUT",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/abort",
            },
        },
    }

    post_response = {
        "id": "654f856d-c602-4347-8713-8f8196d66be3",
        "step": 0,
        "onboardingFactors": [],
        "assessmentStarted": False,
        "locked": False,
        "_links": {
            "startAssessment": {
                "method": "POST",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
            }
        },
    }

    @override_settings(ADA_START_ASSESSMENT_URL="/assessments")
    @patch("ada.utils.post_to_ada", return_value=next_dialog_response)
    @patch("ada.utils.post_to_ada_start_assessment", return_value=post_response)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_start_assessment(
        self, mock_get_rp_payload, mock_post_response, mock_get_response
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {})

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": "",
                "message": (
                    "Welcome to the MomConnect Symptom Checker "
                    "in partnership with Ada. Let's start with some "
                    "questions about the symptoms. Then, we will help "
                    "you decide what to do next.\n\nEnter *back* to go "
                    "to the previous question or *abort* "
                    "to end the assessment"
                ),
                "step": 1,
                "optionId": "",
                "path": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
                "cardType": "TEXT",
                "title": "WELCOME TO ADA",
            },
            response,
        )


class TestMultipleChoiceQuestion(TestCase):
    get_rp_payload = {
        "contact_uuid": "49548747-48888043",
        "choices": "",
        "path": "/assessments/assessment-id/dialog/next",
        "optionId": 0,
        "cardType": "INPUT",
        "step": 2,
        "value": "John",
        "title": "Your name",
    }
    get_from_ada = {
        "cardType": "CHOICE",
        "step": 3,
        "title": {"en-US": "PATIENT INFORMATION"},
        "description": {
            "en-US": (
                "What is John’s biological sex?\nBiological "
                "sex is a risk factor for some conditions. "
                "Your answer is necessary for an accurate assessment."
            )
        },
        "options": [
            {"optionId": 0, "text": {"en-US": "Female"}},
            {"optionId": 1, "text": {"en-US": "Male"}},
        ],
        "_links": {
            "self": {
                "method": "GET",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3",
            },
            "next": {
                "method": "POST",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
            },
            "previous": {
                "method": "POST",
                "href": (
                    "/assessments/"
                    "654f856d-c602-4347-8713-8f8196d66be3/dialog/previous"
                ),
            },
            "abort": {
                "method": "PUT",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/abort",
            },
        },
    }

    @patch.object(AdaAssessment, "save")
    @patch("ada.utils.post_to_ada", return_value=get_from_ada)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_submit_and_get_next_question(
        self, mock_get_rp_payload, mock_post_to_ada, mock_save_mock
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 2, "value": "John"})

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": 2,
                "message": (
                    "What is John’s biological sex?\nBiological "
                    "sex is a risk factor for some conditions. "
                    "Your answer is necessary for an accurate "
                    "assessment.\n\nFemale\nMale\n\nChoose the "
                    "option that matches your answer. Eg, 1 for "
                    "Female\n\nEnter *back* to go to the previous "
                    "question or *abort* to end the assessment"
                ),
                "step": 3,
                "optionId": "",
                "path": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
                "cardType": "CHOICE",
                "title": "PATIENT INFORMATION",
            },
            response,
        )


class TestPreviousMessage(TestCase):
    get_rp_payload = {
        "contact_uuid": "49548747-48888043",
        "choices": "",
        "path": "/assessments/assessment-id/dialog/next",
        "optionId": 1,
        "cardType": "CHOICE",
        "step": 4,
        "value": "back",
        "title": "What symptom",
    }
    previous_dialog_response = {
        "cardType": "CHOICE",
        "step": 3,
        "title": {"en-US": "PATIENT INFORMATION"},
        "description": {
            "en-US": (
                "What is John’s biological sex?\nBiological "
                "sex is a risk factor for some conditions. "
                "Your answer is necessary for an accurate "
                "assessment."
            )
        },
        "options": [
            {"optionId": 0, "text": {"en-US": "Female"}},
            {"optionId": 1, "text": {"en-US": "Male"}},
        ],
        "_links": {
            "self": {
                "method": "GET",
                "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3",
            },
            "next": {
                "method": "POST",
                "href": (
                    "/assessments/" "654f856d-c602-4347-8713-8f8196d66be3/dialog/next"
                ),
            },
            "previous": {
                "method": "POST",
                "href": (
                    "/assessments/"
                    "654f856d-c602-4347-8713-8f8196d66be3/dialog/previous"
                ),
            },
            "abort": {
                "method": "PUT",
                "href": ("/assessments/" "654f856d-c602-4347-8713-8f8196d66be3/abort"),
            },
        },
    }

    @patch("ada.utils.previous_question", return_value=previous_dialog_response)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_submit_and_get_previous_question(
        self, mock_get_rp_payload, mock_post_to_ada
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 4})

        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(
            response,
            {
                "choices": 2,
                "message": (
                    "What is John’s biological sex?\nBiological "
                    "sex is a risk factor for some conditions. "
                    "Your answer is necessary for an accurate "
                    "assessment.\n\nFemale\nMale\n\nChoose the "
                    "option that matches your answer. Eg, 1 for "
                    "Female\n\nEnter *back* to go to the previous "
                    "question or *abort* to end the assessment"
                ),
                "step": 3,
                "optionId": "",
                "path": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
                "cardType": "CHOICE",
                "title": "PATIENT INFORMATION",
            },
            response,
        )


class TestReturnReport(TestCase):
    get_rp_payload = {
        "contact_uuid": "49548747-48888043",
        "choices": "",
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

    @patch.object(AdaAssessment, "save")
    @patch("ada.utils.get_report", return_value=report_reponse)
    @patch("ada.utils.post_to_ada", return_value=get_from_ada)
    @patch("ada.utils.get_rp_payload", return_value=get_rp_payload)
    def test_get_report(
        self, mock_get_rp_payload, mock_post_response, mock_get_report, mock_save_mock
    ):

        request_to_ada = utils.build_rp_request(mock_get_rp_payload.return_value)
        self.assertEqual(request_to_ada, {"step": 15})
        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(response, {"pdf sent"}, response)
