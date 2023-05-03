import json
from unittest import TestCase

import responses

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
                    "\nReply *EXIT* to exit the symptom checker."
                ),
                "explanations": "",
                "step": 1,
                "optionId": None,
                "path": "/assessments/654f856d-c602-4347-8713-8f8196d66be3/dialog/next",
                "cardType": "TEXT",
                "description": (
                    "Welcome to the MomConnect Symptom "
                    "Checker in partnership with Ada. "
                    "Let's start with some questions about "
                    "the symptoms. Then, we will help you "
                    "decide what to do next."
                ),
                "pdf_media_id": "",
                "title": "",
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
                "choices": 3,
                "choiceContext": (
                    ["Female", "Male", "I don't understand what this means."]
                ),
                "resource": "",
                "message": (
                    "Hi John, what is your biological sex?"
                    "\nBiological sex is a risk factor for some "
                    "conditions. Your answer is necessary for an "
                    "accurate assessment.\n\n*1 -* Female\n*2 -* Male\n*3 "
                    "-* I don't understand what this means."
                    "\n\nReply *BACK* to go to the previous "
                    "question."
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
                "description": (
                    "Hi John, what is your biological sex?\n"
                    "Biological sex is a risk factor for "
                    "some conditions. Your answer is necessary "
                    "for an accurate assessment."
                ),
                "pdf_media_id": "",
                "title": "",
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
            "pattern": "",
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
                "pattern": "",
                "message": (
                    "How old are you?\n\n"
                    '_Enter age in years, for example "20"_\n\n'
                    "Reply *BACK* to go to "
                    "the previous question."
                ),
                "explanations": "",
                "step": 5,
                "optionId": None,
                "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
                "cardType": "INPUT",
                "description": "How old are you?",
                "pdf_media_id": "",
                "title": "",
            },
            response,
        )

    def test_input_type_regex(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "msisdn": "27856454612",
            "choiceContext": "",
            "choices": "",
            "path": "/assessments/assessment-id/dialog/next",
            "optionId": 0,
            "cardType": "INPUT",
            "step": 5,
            "value": "John",
            "title": "Your name",
            "pattern": "",
        }
        ada_response = {
            "cardType": "INPUT",
            "step": 9,
            "title": {"en-GB": "Patient Information"},
            "description": {"en-GB": "How old is ChimaC?"},
            "cardAttributes": {
                "format": "integer",
                "maximum": {
                    "value": 13,
                    "message": (
                        "Age must be 13 days or " "younger to assess the symptoms."
                    ),
                },
                "pattern": {
                    "value": "^\\d+$",
                    "message": (
                        "Age must only include numbers. Please "
                        "enter a correct value, for example '3'."
                    ),
                },
                "placeholder": {"en-GB": 'Please type age in days, for example "3".'},
            },
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/a225966f-40c8-45e3-b597-e1a45f0dd751",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/a225966f-40c8-45e3"
                        "-b597-e1a45f0dd751/dialog/next"
                    ),
                },
                "previous": {
                    "method": "POST",
                    "href": (
                        "/assessments/a225966f-40c8-45e3"
                        "-b597-e1a45f0dd751/dialog/previous"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/a225966f-40c8-45e3-b597-e1a45f0dd751/abort",
                },
            },
        }

        request_to_ada = utils.build_rp_request(rapidpro_data)
        self.assertEqual(request_to_ada, {"step": 5, "value": "John"})

        response = utils.format_message(ada_response)
        self.assertEqual(
            response,
            {
                "choices": None,
                "formatType": "integer",
                "max": 13,
                "max_error": "Age must be 13 days or younger to assess the symptoms.",
                "min": "^\\d+$",
                "min_error": (
                    "Age must only include numbers. Please enter a correct value, "
                    "for example '3'."
                ),
                "pattern": "^\\d+$",
                "message": (
                    "How old is ChimaC?\n\n_Please "
                    'type age in days, for example "3"._\n\n'
                    "Reply *BACK* to go to the previous "
                    "question."
                ),
                "explanations": "",
                "step": 9,
                "optionId": None,
                "path": "/assessments/a225966f-40c8-45e3-b597-e1a45f0dd751/dialog/next",
                "cardType": "INPUT",
                "description": "How old is ChimaC?",
                "pdf_media_id": "",
                "title": "",
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
                    "\n\nReply:\n*CHECK* if you would like to check "
                    "another symptom\n*MENU* for the MomConnect menu 📌"
                ),
                "explanations": "",
                "step": 43,
                "optionId": None,
                "path": "",
                "cardType": "REPORT",
                "description": (
                    "People with symptoms similar to yours do not usually "
                    "require urgent medical care. You should seek advice "
                    "from a doctor though, within the next 2-3 days. If "
                    "your symptoms get worse, or if you notice new "
                    "symptoms, you may need to consult a doctor sooner."
                ),
                "pdf_media_id": "",
                "title": "",
            },
            response,
        )

    def test_display_title(self):
        rapidpro_data = {
            "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
            "msisdn": "27856454612",
            "choiceContext": "",
            "choices": "",
            "path": "",
            "optionId": None,
            "cardType": "",
            "step": None,
            "value": "",
            "title": "",
            "pattern": "",
        }
        ada_response = {
            "cardType": "TEXT",
            "step": 1,
            "title": {"en-GB": "Disclaimer"},
            "description": {
                "en-GB": (
                    "If you have any of the following symptoms "
                    "do NOT complete the assessment. Call your "
                    "local emergency number now.\n\n- Signs of "
                    "heart attack (heavy, tight or squeezing "
                    "pain in your chest)\n- Signs of stroke "
                    "(face dropping on one side, weakness "
                    "of the arms / legs, difficulty speaking)"
                    "\n- Severe difficulty breathing \n- Heavy "
                    "bleeding\n- Severe injuries such as after "
                    "an accident\n- A seizure or fit\n- Sudden "
                    "rapid swelling of eyes, lips, mouth or "
                    "tongue\n- Fever in a baby less than 3 "
                    "months old"
                )
            },
            "label": {"en-GB": "Next"},
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/99c4df73-ff27-4b3e-ac40-fcfb15da13ac",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/99c4df73-ff27-"
                        "4b3e-ac40-fcfb15da13ac/dialog/next"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/99c4df73-ff27-4b3e-ac40-fcfb15da13ac/abort",
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
                    "If you have any of the following "
                    "symptoms do NOT complete the assessment. "
                    "Call your local emergency number now.\n\n- "
                    "Signs of heart attack (heavy, tight or "
                    "squeezing pain in your chest)\n- Signs of "
                    "stroke (face dropping on one side, weakness "
                    "of the arms / legs, difficulty speaking)\n- "
                    "Severe difficulty breathing \n- Heavy "
                    "bleeding\n- Severe injuries such as after "
                    "an accident\n- A seizure or fit\n- Sudden "
                    "rapid swelling of eyes, lips, mouth or "
                    "tongue\n- Fever in a baby less than 3 months "
                    "old\n\nReply *0* to continue.\nReply *EXIT* "
                    "to exit the symptom checker."
                ),
                "explanations": "",
                "step": 1,
                "optionId": None,
                "path": (
                    "/assessments/99c4df73-ff27-4b3e-ac40" "-fcfb15da13ac/dialog/next"
                ),
                "cardType": "TEXT",
                "description": (
                    "If you have any of the following "
                    "symptoms do NOT complete the assessment. "
                    "Call your local emergency number now."
                    "\n\n- Signs of heart attack (heavy, tight "
                    "or squeezing pain in your chest)\n- Signs "
                    "of stroke (face dropping on one side, "
                    "weakness of the arms / legs, difficulty "
                    "speaking)\n- Severe difficulty breathing "
                    "\n- Heavy bleeding\n- Severe injuries such "
                    "as after an accident\n- A seizure or fit\n- "
                    "Sudden rapid swelling of eyes, lips, mouth "
                    "or tongue\n- Fever in a baby less than 3 "
                    "months old"
                ),
                "pdf_media_id": "",
                "title": "*Disclaimer*",
            },
        )


class TestCovidDataLake(TestCase):
    def test_text_type_question(self):
        payload = {
            "payload": {
                "resourceType": "Bundle",
                "id": "35e6" "cde9d29e47acda1042def0b10db8",
                "meta": {"last" "Updated": "2022-07-03T20:28:49.763+00:00"},
            }
        }
        resource_id = payload["payload"]["id"]
        self.assertEqual(resource_id, "35e6cde9d29e47acda1042def0b10db8")


class TestCreateCastorRecord(TestCase):
    @responses.activate
    def test_create_castor_record(self):
        responses.add(
            responses.POST,
            "http://castor/test-study-id/record",
            json={"record_id": "record-id"},
        )
        record_id = utils.create_castor_record("token-uuid")

        self.assertEqual(record_id, "record-id")

        [call] = responses.calls

        self.assertEqual(call.request.headers["Authorization"], "Bearer token-uuid")
        self.assertEqual(
            json.loads(call.request.body), {"institute_id": "test-institute-id"}
        )


class TestSubmitCastorData(TestCase):
    @responses.activate
    def test_submit_castor_data(self):
        responses.add(
            responses.POST,
            "http://castor/test-study-id/record/record-id/study-data-point/field-uuid",
            json={},
        )
        utils.submit_castor_data("token-uuid", "record-id", "field-uuid", "field-value")

        [call] = responses.calls

        self.assertEqual(call.request.headers["Authorization"], "Bearer token-uuid")
        self.assertEqual(json.loads(call.request.body), {"field_value": "field-value"})


class TestCleanFilename(TestCase):
    def test_clean_filename(self):
        file_name = utils.clean_filename("7566422 0001 0001'#{ report.json")
        self.assertEqual(file_name, "7566422_0001_0001_report.json")
