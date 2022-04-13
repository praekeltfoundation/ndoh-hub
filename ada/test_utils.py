from unittest import TestCase

from ada import utils


class TestQuestionsPayload(TestCase):
    def test_text_type_question(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "choices": None,
            "value": "",
            "cardType": "",
            "step": None,
            "optionId": None,
            "path": "",
            "title": "",
        }
        ada_response = {
            "cardType": "TEXT",
            "step": 1,
            "title": {"en-GB": "WELCOME TO ADA"},
            "description": {
                "en-GB": (
                    "Welcome to the MomConnect Symptom Checker in "
                    "partnership with Ada. Let's start with some questions "
                    "about the symptoms. Then, we will help you "
                    "decide what to do next."
                )
            },
            "label": {"en-GB": "Continue"},
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "654f856d-c602-4347-8713-8f8196d66be3/dialog/next"
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
                    "href": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/abort",
                },
            },
        }

        request_to_ada = utils.build_rp_request(rapidpro_data)
        self.assertEqual(request_to_ada, {})

        response = utils.format_message(ada_response)
        self.assertEqual(
            response,
            {
                "message": (
                    "Welcome to the MomConnect Symptom "
                    "Checker in partnership with Ada. Let's "
                    "start with some questions about the symptoms. "
                    "Then, we will help you decide what to do next."
                    "\n\nReply '0' to continue."
                    "\n\nReply *back* to go to the previous question "
                    "or *abort* to end the assessment"
                ),
                "explanations": "",
                "step": 1,
                "optionId": None,
                "path": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
                "cardType": "TEXT",
                "title": "WELCOME TO ADA",
                "description": (
                    "Welcome to the MomConnect Symptom "
                    "Checker in partnership with Ada. "
                    "Let's start with some questions about "
                    "the symptoms. Then, we will help you "
                    "decide what to do next."
                ),
            },
            response,
        )

    def test_choice_type_question(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "choices": "",
            "path": "/assessments/assessment-id/dialog/next",
            "optionId": 0,
            "cardType": "INPUT",
            "step": 3,
            "value": "John",
            "title": "Your name",
        }
        ada_response = {
            "cardType": "CHOICE",
            "step": 4,
            "title": {"en-GB": "Patient Information"},
            "description": {
                "en-GB": (
                    "Hi John, what is your biological sex?\nBiological "
                    "sex is a risk factor for some conditions. "
                    "Your answer is necessary for an accurate assessment."
                )
            },
            "explanations": [
                {
                    "label": {"en-GB": "Why only these 2?"},
                    "text": {
                        "en-GB": (
                            "We are investigating a solution "
                            "to provide a more inclusive health assessment "
                            "for people beyond the binary options of female "
                            "or male.\n&nbsp;\nYour feedback can help. "
                            "Please share how this assessment could support "
                            "your needs better by emailing support@ada.com"
                            "\n&nbsp;\nFor now, unfortunately, a medically "
                            "accurate assessment can only be provided if "
                            "you select female or male."
                        )
                    },
                }
            ],
            "options": [
                {"optionId": 0, "text": {"en-GB": "Female"}},
                {"optionId": 1, "text": {"en-GB": "Male"}},
            ],
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next"
                    ),
                },
                "previous": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/previous"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/abort",
                },
            },
        }

        request_to_ada = utils.build_rp_request(rapidpro_data)
        self.assertEqual(request_to_ada, {"step": 3, "value": "John"})

        response = utils.format_message(ada_response)
        self.assertEqual(
            response,
            {
                "choices": 2,
                "message": (
                    "Hi John, what is your biological sex?"
                    "\nBiological sex is a risk factor for some "
                    "conditions. Your answer is necessary for an "
                    "accurate assessment.\n\nFemale\nMale\n\nChoose "
                    "the option that matches your answer. Eg, 1 for "
                    "Female\n\nReply *back* to go to the previous "
                    "question or *abort* to end the assessment"
                ),
                "explanations": (
                    "We are investigating a solution "
                    "to provide a more inclusive health assessment "
                    "for people beyond the binary options of female "
                    "or male.\n&nbsp;\nYour feedback can help. Please "
                    "share how this assessment could support your needs "
                    "better by emailing support@ada.com\n&nbsp;\nFor "
                    "now, unfortunately, a medically accurate assessment "
                    "can only be provided if you select female or male."
                ),
                "step": 4,
                "optionId": None,
                "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
                "cardType": "CHOICE",
                "title": "Patient Information",
                "description": (
                    "Hi John, what is your biological sex?\n"
                    "Biological sex is a risk factor for "
                    "some conditions. Your answer is necessary "
                    "for an accurate assessment."
                ),
            },
            response,
        )

    def test_input_type_question(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "choices": "",
            "path": "/assessments/assessment-id/dialog/next",
            "optionId": 0,
            "cardType": "INPUT",
            "step": 4,
            "value": "John",
            "title": "Your name",
        }
        ada_response = {
            "cardType": "INPUT",
            "step": 5,
            "title": {"en-GB": "Patient Information"},
            "description": {"en-GB": "How old are you?"},
            "cardAttributes": {
                "format": "integer",
                "maximum": {
                    "value": 120,
                    "message": (
                        "Age must be 120 years or younger " "to assess the symptoms"
                    ),
                },
                "minimum": {
                    "value": 16,
                    "message": (
                        "Age must be 16 years or older " "to assess your symptoms"
                    ),
                },
                "pattern": {
                    "value": "^\\d+$",
                    "message": (
                        "Age must only include numbers. "
                        'Please enter a correct value, for example "20"'
                    ),
                },
                "placeholder": {"en-GB": 'Enter age in years, for example "20"'},
            },
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next"
                    ),
                },
                "previous": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/previous"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/abort",
                },
            },
        }

        request_to_ada = utils.build_rp_request(rapidpro_data)
        self.assertEqual(request_to_ada, {"step": 4, "value": "John"})

        response = utils.format_message(ada_response)
        self.assertEqual(
            response,
            {
                "choices": None,
                "message": (
                    "How old are you?\n\nReply *back* to go to "
                    "the previous question or *abort* to "
                    "end the assessment"
                ),
                "explanations": "",
                "step": 5,
                "optionId": None,
                "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
                "cardType": "INPUT",
                "title": "Patient Information",
                "description": "How old are you?",
            },
            response,
        )
