from unittest import TestCase

from ada import utils


class TestQuestionsPayload(TestCase):
    def test_text_type_question(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "msisdn": "",
            "choiceContext": "",
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
                    "\n\nReply *0* to continue."
                    "\n\nReply *BACK* to go to the previous question "
                    "or *MENU* to end the assessment."
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
            "msisdn": "27856454612",
            "choiceContext": "",
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
                "choiceContext": ["Female", "Male"],
                "resource": "",
                "message": (
                    "Hi John, what is your biological sex?"
                    "\nBiological sex is a risk factor for some "
                    "conditions. Your answer is necessary for an "
                    "accurate assessment.\n\n1. Female\n2. Male\n\nChoose "
                    "the option that matches your answer. Eg, *1* for "
                    "*Female*\n\nReply *BACK* to go to the previous "
                    "question or *MENU* to end the assessment."
                    "\n\nReply *EXPLAIN* to see what this means."
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
            "msisdn": "27856454612",
            "choiceContext": "",
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
                "formatType": "integer",
                "max": 120,
                "max_error": "Age must be 120 years or younger to assess the symptoms",
                "min": 16,
                "min_error": "Age must be 16 years or older to assess your symptoms",
                "message": (
                    "How old are you?\n\n"
                    '_Enter age in years, for example "20"_\n\n'
                    "Reply *BACK* to go to "
                    "the previous question or *MENU* to "
                    "end the assessment."
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

    def test_report_cardtype(self):
        ada_response = {
            "cardType": "REPORT",
            "step": 43,
            "title": {"en-GB": "Results"},
            "description": {
                "en-GB": (
                    "People with symptoms similar to yours do not "
                    "usually require urgent medical care. "
                    "You should seek advice from a doctor though, "
                    "within the next 2-3 days. If your symptoms "
                    "get worse, or if you notice new symptoms, "
                    "you may need to consult a doctor sooner."
                )
            },
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/5581bfeb-2803-4beb-b627-9f9d2a5651d8",
                },
                "report": {
                    "method": "GET",
                    "href": "/reports/5581bfeb-2803-4beb-b627-9f9d2a5651d8",
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/5581bfeb-2803-4beb-b627-9f9d2a5651d8/abort",
                },
            },
        }

        response = utils.format_message(ada_response)
        self.assertEqual(
            response,
            {
                "message": (
                    "People with symptoms similar to "
                    "yours do not usually require urgent "
                    "medical care. You should seek advice "
                    "from a doctor though, within the next 2-3 days. "
                    "If your symptoms get worse, or if you notice "
                    "new symptoms, you may need to consult a doctor sooner."
                    "\n\nReply:\n\n*1* - *CHECK* to check another symptom\n\n"
                    "*2* - *ASK* to ask the helpdesk a question\n\n"
                    "*3* - *MENU* for the MomConnect menu 📌"
                ),
                "explanations": "",
                "step": 43,
                "optionId": None,
                "path": "",
                "cardType": "REPORT",
                "title": "Results",
                "description": (
                    "People with symptoms similar to yours do not usually "
                    "require urgent medical care. You should seek advice "
                    "from a doctor though, within the next 2-3 days. If "
                    "your symptoms get worse, or if you notice new "
                    "symptoms, you may need to consult a doctor sooner."
                ),
            },
            response,
        )
