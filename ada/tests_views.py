import json
from unittest.mock import patch
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ada import utils

from .models import RedirectUrl


class TestViews(TestCase):
    def test_whatsapp_url_error(self):
        """
        Should check that the right template is used for no whatsapp string in url
        """
        response = self.client.get(reverse("ada_hook", args=["1"]))
        self.assertTemplateUsed(response, "index.html")

    def test_name_error(self):
        """
        Should check that the right template is used for mis-spelt whatsappid
        """
        qs = "?whatsappi=12345"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_no_whatsapp_value(self):
        """
        Should check that the right template is used if no whatsapp value
        """
        qs = "?whatsapp="
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_no_query_string(self):
        """
        Should check that the right template is used if no whatsapp value
        """
        qs = "?"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_name_success(self):
        """
        Should use the meta refresh template if url is correct
        """
        qs = "?whatsappid=12345"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "meta_refresh.html")


class AdaHookViewTests(TestCase):
    def setUp(self):
        super(AdaHookViewTests, self).setUp()
        self.post = RedirectUrl.objects.create(
            content="Entry has no copy",
            symptom_check_url="http://symptomcheck.co.za",
            parameter="1",
            time_stamp="2021-05-06 07:24:14.014990+00:00",
        )

    def tearDown(self):
        super(AdaHookViewTests, self).tearDown()
        self.post.delete()

    def test_ada_hook_redirect_success(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=(self.post.id, "1235"))
        )
        self.assertEqual(response.status_code, 302)

    # check that symptom check url has the right query parameters
    def test_ada_hook_redirect_content(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=(self.post.id, "1235"))
        )
        self.assertEqual(
            response.url,
            "http://symptomcheck.co.za?whatsappid=1235&customizationId=kh93qnNLps",
        )

    # Raise HTTp404 if RedirectUrl does not exist
    def test_ada_hook_redirect_404(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=("1", "27789049372"))
        )
        self.assertEqual(response.status_code, 404)

    # Raise HTTp404 if ValueError
    def test_ada_hook_redirect_404_nameError(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=("invalidurlid", "invalidwhatsappid"))
        )
        self.assertEqual(response.status_code, 404)


class AdaSymptomCheckEndpointTests(APITestCase):
    url = reverse("rapidpro_start_flow")
    topup_url = reverse("rapidpro_topup_flow")

    @patch("ada.views.start_prototype_survey_flow")
    def test_unauthenticated(self, mock_start_rapidpro_flow):
        whatsappid = "12345"

        response = self.client.post(self.url, {"whatsappid": whatsappid})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        mock_start_rapidpro_flow.delay.assert_not_called()

    @patch("ada.views.start_prototype_survey_flow")
    def test_invalid_data(self, mock_start_rapidpro_flow):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {"whatsapp": "123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"whatsappid": ["This field is required."]})

        mock_start_rapidpro_flow.delay.assert_not_called()

    @patch("ada.views.start_prototype_survey_flow")
    def test_unsuccessful_flow_start(self, mock_start_rapidpro_flow):
        whatsappid = "endToEndTestWhatsappid"

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {"whatsappid": whatsappid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_start_rapidpro_flow.delay.assert_not_called()

    @patch("ada.views.start_prototype_survey_flow")
    def test_successful_flow_start(self, mock_start_rapidpro_flow):
        whatsappid = "+274844444444"

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {"whatsappid": whatsappid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_start_rapidpro_flow.delay.assert_called_once_with(whatsappid)

    @patch("ada.views.start_topup_flow")
    def test_invalid_post_data(self, mock_start_rapidpro_topup_flow):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.topup_url, {"whatsapp": "123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"whatsappid": ["This field is required."]})

        mock_start_rapidpro_topup_flow.delay.assert_not_called()

    @patch("ada.views.start_topup_flow")
    def test_successful_topup_flow_start(self, mock_start_rapidpro_topup_flow):
        whatsappid = "12345"

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.topup_url, {"whatsappid": whatsappid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_start_rapidpro_topup_flow.delay.assert_called_once_with(whatsappid)


class AdaValidationViewTests(APITestCase):
    # Return validation error if user input > 100 characters for an input cardType
    def test_input_type(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-assessments"),
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "message": (
                        "Please type in the symptom that is troubling you, "
                        "only one symptom at a time. Reply back to go to the "
                        "previous question or menu to end the assessment."
                    ),
                    "step": 4,
                    "value": (
                        "This is some rubbish text to see what happens when a "
                        "user submits an input with a length that is "
                        "greater than 100"
                    ),
                    "optionId": 8,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "INPUT",
                    "title": "SYMPTOM",
                    "formatType": "string",
                    "max": None,
                    "max_error": "",
                    "min": None,
                    "min_error": "",
                    "pattern": "",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "message": (
                    "Please type in the symptom that is troubling you, "
                    "only one symptom at a time. Reply back to go to the "
                    "previous question or menu to end the assessment."
                ),
                "step": "4",
                "value": (
                    "This is some rubbish text to see what happens "
                    "when a user submits an input with a length that"
                    " is greater than 100"
                ),
                "optionId": "8",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "INPUT",
                "title": "SYMPTOM",
                "formatType": "string",
                "error": (
                    "We are sorry, your reply should be "
                    "between *1* and *100* characters."
                ),
                "max": "None",
                "max_error": "",
                "min": "None",
                "min_error": "",
                "pattern": "",
            },
            response.json(),
        )

    def test_input_type_error_string(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-assessments"),
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "message": (
                        "Please type in the symptom that is troubling you, "
                        "only one symptom at a time. Reply back to go to the "
                        "previous question or menu to end the assessment."
                    ),
                    "step": 4,
                    "value": ("1998"),
                    "optionId": 8,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "INPUT",
                    "title": "SYMPTOM",
                    "formatType": "string",
                    "max": None,
                    "max_error": "",
                    "min": None,
                    "min_error": "",
                    "pattern": "",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "message": (
                    "Please type in the symptom "
                    "that is troubling you, "
                    "only one symptom at a time. "
                    "Reply back to go to the previous "
                    "question or menu to end the assessment."
                ),
                "step": "4",
                "value": "1998",
                "optionId": "8",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "INPUT",
                "title": "SYMPTOM",
                "formatType": "string",
                "max": "None",
                "max_error": "",
                "min": "None",
                "min_error": "",
                "error": (
                    "Sorry, we didn't understand your answer. "
                    "Your reply must only include text."
                ),
                "pattern": "",
            },
            response.json(),
        )

    def test_input_type_error_integer(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-assessments"),
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "message": ("Enter age in years"),
                    "step": 4,
                    "value": ("I am 18 years old"),
                    "optionId": 8,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "INPUT",
                    "title": "SYMPTOM",
                    "formatType": "integer",
                    "max": 120,
                    "max_error": (
                        "Age must be 120 years or younger " "to assess the symptoms"
                    ),
                    "min": 1,
                    "min_error": (
                        "Age in years must be greater than " "0 to assess the symptoms"
                    ),
                    "pattern": "",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "message": ("Enter age in years"),
                "step": "4",
                "value": "I am 18 years old",
                "optionId": "8",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "INPUT",
                "title": "SYMPTOM",
                "formatType": "integer",
                "error": (
                    "Sorry, we didn't understand your answer. "
                    "Your reply must only include numbers."
                ),
                "max": "120",
                "max_error": "Age must be 120 years or younger to assess the symptoms",
                "min": "1",
                "min_error": (
                    "Age in years must be greater than 0 " "to assess the symptoms"
                ),
                "pattern": "",
            },
            response.json(),
        )

    def test_input_type_error_regex(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-assessments"),
            json.dumps(
                {
                    "choices": None,
                    "msisdn": "27856454612",
                    "message": (
                        "How old is ChimaC?\n\n_Please "
                        'type age in days, for example "3"._\n\n'
                        "Reply *BACK* to go to the previous "
                        "question or *MENU* to end the assessment."
                    ),
                    "step": 9,
                    "value": "He is 25 years old",
                    "optionId": None,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "INPUT",
                    "title": "Patient Information",
                    "formatType": "integer",
                    "max": 13,
                    "max_error": (
                        "Age must be 13 days or younger to assess the symptoms."
                    ),
                    "min": "^\\d+$",
                    "min_error": (
                        "Age must only include numbers. Please enter a correct value, "
                        "for example '3'."
                    ),
                    "pattern": "^\\d+$",
                    "explanations": "",
                    "title": "Patient Information",
                    "description": "How old is ChimaC?",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "choices": "None",
                "msisdn": "27856454612",
                "message": (
                    "How old is ChimaC?\n\n_Please "
                    'type age in days, for example "3"._\n\n'
                    "Reply *BACK* to go to the previous "
                    "question or *MENU* to end the assessment."
                ),
                "step": "9",
                "value": "He is 25 years old",
                "optionId": "None",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "INPUT",
                "title": "Patient Information",
                "formatType": "integer",
                "max": "13",
                "max_error": "Age must be 13 days or younger to assess the symptoms.",
                "min": "^\\d+$",
                "min_error": (
                    "Age must only include numbers. Please enter a correct value, "
                    "for example '3'."
                ),
                "pattern": "^\\d+$",
                "explanations": "",
                "description": "How old is ChimaC?",
                "error": (
                    "Age must only include numbers. "
                    "Please enter a correct value, for example '3'."
                ),
            },
            response.json(),
        )

    # Return validation error for invalid choice for CHOICE cardType
    url = reverse("ada-assessments")

    def test_choice_type(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "choices": 3,
                    "choiceContext": ["Abdominal pain", "Headache"],
                    "message": (
                        "What is the issue?\n\nAbdominal pain\n"
                        "Headache"
                        "\nNone of these\n\nChoose the option that matches "
                        "your answer. "
                        "Eg, *1* for *Abdominal pain*\n\nEnter *BACK* to go "
                        "to the previous question or *MENU* "
                        "to end the assessment."
                    ),
                    "step": 4,
                    "value": "9",
                    "optionId": 0,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "CHOICE",
                    "title": "SYMPTOM",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "choices": "3",
                "choiceContext": ["Abdominal pain", "Headache"],
                "message": (
                    "What is the issue?\n\nAbdominal pain\nHeadache"
                    "\nNone of these\n\nChoose the option that "
                    "matches your answer. "
                    "Eg, *1* for *Abdominal pain*\n\nEnter *BACK* to go "
                    "to the previous question or *MENU* "
                    "to end the assessment."
                ),
                "step": "4",
                "value": "9",
                "optionId": "0",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "CHOICE",
                "title": "SYMPTOM",
                "error": (
                    "Something seems to have gone wrong. You "
                    "entered 9 but there are 3 options. "
                    "Please reply with a number between 1 and 3."
                ),
            },
            response.json(),
        )

        response = self.client.post(
            self.url,
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "choices": 3,
                    "choiceContext": ["Abdominal pain", "Headache"],
                    "message": (
                        "What is the issue?\n\nAbdominal pain\n"
                        "Headache"
                        "\nNone of these\n\nChoose the option that matches "
                        "your answer. "
                        "Eg, *1* for *Abdominal pain*\n\nEnter *BACK* to go "
                        "to the previous question or *MENU* "
                        "to end the assessment."
                    ),
                    "step": 4,
                    "value": "0",
                    "optionId": 0,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "CHOICE",
                    "title": "SYMPTOM",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "choices": "3",
                "choiceContext": ["Abdominal pain", "Headache"],
                "message": (
                    "What is the issue?\n\nAbdominal pain\nHeadache"
                    "\nNone of these\n\nChoose the option that "
                    "matches your answer. "
                    "Eg, *1* for *Abdominal pain*\n\nEnter *BACK* to go "
                    "to the previous question or *MENU* "
                    "to end the assessment."
                ),
                "step": "4",
                "value": "0",
                "optionId": "0",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "CHOICE",
                "title": "SYMPTOM",
                "error": (
                    "Something seems to have gone wrong. You "
                    "entered 0 but there are 3 options. "
                    "Please reply with a number between 1 and 3."
                ),
            },
            response.json(),
        )

    # Return validation error for invalid choice for text cardType
    def test_text_type(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-assessments"),
            json.dumps(
                {
                    "msisdn": "27856454612",
                    "choices": None,
                    "message": (
                        "Welcome to the MomConnect Symptom Checker in "
                        "partnership with Ada. Let's start with some questions "
                        "about the symptoms. Then, we will help you "
                        "decide what to do next."
                    ),
                    "step": 4,
                    "value": "",
                    "optionId": None,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "TEXT",
                    "title": "WELCOME",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "msisdn": "27856454612",
                "choices": "None",
                "message": (
                    "Welcome to the MomConnect Symptom Checker in "
                    "partnership with Ada. Let's start with some questions "
                    "about the symptoms. Then, we will help you "
                    "decide what to do next."
                ),
                "step": "4",
                "value": "",
                "optionId": "None",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "TEXT",
                "title": "WELCOME",
                "error": "Please reply *continue*, *0* or *accept* to continue.",
            },
            response.json(),
        )


class StartAssessment(APITestCase):
    data = {
        "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
        "msisdn": "",
        "choiceContext": "",
        "choices": "None",
        "message": "",
        "step": "None",
        "value": "",
        "optionId": "None",
        "path": "",
        "cardType": "",
        "title": "",
    }
    url = reverse("ada-assessments")
    url_start_assessment = reverse("ada-start-assessment")
    destination_url = (
        "/api/v2/ada/startassessment?contact_uuid"
        "=67460e74-02e3-11e8-b443-00163e990bdb"
        "&msisdn=&choiceContext=&choices"
        "=None&message=&step=None&value=&optionId"
        "=None&path=&cardType=&title="
    )

    @patch("ada.views.post_to_ada")
    @patch("ada.views.post_to_ada_start_assessment")
    @patch("ada.views.get_endpoint")
    def test_start_assessment(
        self, mock_get_endpoint, mock_post_to_ada_start_assessment, mock_post_to_ada
    ):

        mock_post_to_ada_start_assessment.return_value = {
            "id": "052a482d-8b77-4e48-b198-ade28485bf3f",
            "step": 0,
            "isPrimaryUser": "true",
            "onboardingFactors": [],
            "assessmentStarted": "false",
            "locked": "false",
            "_links": {
                "startAssessment": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "052a482d-8b77-4e48-b198-ade28485bf3f/dialog/next"
                    ),
                }
            },
        }

        mock_post_to_ada.return_value = {
            "cardType": "TEXT",
            "step": 1,
            "title": {"en-GB": "Welcome to Ada"},
            "description": {
                "en-GB": (
                    "Welcome to the MomConnect Symptom "
                    "Checker in partnership with Ada. "
                    "Let's start with some questions "
                    "about the symptoms. Then, we will "
                    "help you decide what to do next."
                )
            },
            "label": {"en-GB": "Continue"},
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/880c70ca-0bf7-40e7-826d-db6ccfcc6b37",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "880c70ca-0bf7-40e7-826d-db6ccfcc6b37/dialog/next"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/880c70ca-0bf7-40e7-826d-db6ccfcc6b37/abort",
                },
            },
        }

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        mock_get_endpoint.return_value = self.url_start_assessment
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, self.destination_url)


class AdaAssessmentDialog(APITestCase):
    data = {
        "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
        "msisdn": "27856454612",
        "choiceContext": "",
        "choices": None,
        "message": "",
        "step": None,
        "value": "",
        "optionId": None,
        "path": "",
        "cardType": "",
        "title": "",
        "formatType": "integer",
    }

    data_next_dialog = {
        "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
        "msisdn": "27856454612",
        "choiceContext": "",
        "choices": None,
        "message": (
            "How old are you?\n\nReply *BACK* to go to "
            "the previous question or *MENU* to "
            "end the assessment"
        ),
        "explanations": "",
        "step": 5,
        "value": "27",
        "optionId": None,
        "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
        "cardType": "INPUT",
        "title": "Patient Information",
        "description": "How old are you?",
        "formatType": "integer",
        "max": 120,
        "max_error": "Age must be 120 years or younger to assess the symptoms",
        "min": 1,
        "min_error": "Age in years must be greater than 0 to assess the symptoms",
        "pattern": "",
    }

    roadblock_dialog = {
        "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdb",
        "msisdn": "27856454612",
        "choiceContext": "",
        "choices": None,
        "message": (
            "Are you sure you want to end?\n\nReply *BACK* to go to "
            "the previous question or *MENU* to "
            "end the assessment"
        ),
        "explanations": "",
        "step": 25,
        "value": "Yes",
        "optionId": None,
        "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
        "cardType": "INPUT",
        "title": "Roadblock warning",
        "description": "Roadblock warning",
        "formatType": "string",
        "max": None,
        "max_error": "",
        "min": None,
        "min_error": "",
        "pattern": "",
    }

    entry_url = reverse("ada-assessments")
    url = reverse("ada-next-dialog")

    @patch("ada.views.post_to_ada_start_assessment")
    @patch("ada.views.post_to_ada")
    def test_first_dialog(self, mock_post_to_ada_start_assessment, mock_post_to_ada):
        request = utils.build_rp_request(self.data)
        self.assertEqual(request, {})
        mock_post_to_ada_start_assessment.return_value = {
            "id": "976663c1-aa5e-4d3b-8455-9980fc3f26ca",
            "step": 0,
            "isPrimaryUser": "true",
            "onboardingFactors": [],
            "assessmentStarted": "false",
            "locked": "false",
            "_links": {
                "startAssessment": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "976663c1-aa5e-4d3b-8455-9980fc3f26ca/dialog/next"
                    ),
                }
            },
        }

        mock_post_to_ada.return_value = {
            "cardType": "TEXT",
            "step": 1,
            "title": {"en-GB": "Welcome to Ada"},
            "description": {
                "en-GB": (
                    "Welcome to the MomConnect Symptom Checker "
                    "in partnership with Ada. Let's start with "
                    "some questions about the symptoms. Then, "
                    "we will help you decide what to do next."
                )
            },
            "label": {"en-GB": "Continue"},
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/976663c1-aa5e-4d3b-8455-9980fc3f26ca",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "976663c1-aa5e-4d3b-8455-9980fc3f26ca/dialog/next"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/976663c1-aa5e-4d3b-8455-9980fc3f26ca/abort",
                },
            },
        }

        path = utils.get_path(mock_post_to_ada_start_assessment.return_value)
        self.assertEqual(
            path, "/assessments/976663c1-aa5e-4d3b-8455-9980fc3f26ca/dialog/next"
        )
        step = utils.get_step(mock_post_to_ada_start_assessment.return_value)
        self.assertEqual(step, 0)
        request = utils.build_rp_request(mock_post_to_ada_start_assessment.return_value)
        message = utils.format_message(mock_post_to_ada.return_value)
        self.assertEqual(
            message,
            {
                "message": (
                    "Welcome to the MomConnect Symptom Checker "
                    "in partnership with Ada. Let's start with "
                    "some questions about the symptoms. Then, "
                    "we will help you decide what to do next."
                    "\n\nReply *0* to continue.\nReply "
                    "*EXIT* to exit the symptom checker."
                ),
                "explanations": "",
                "step": 1,
                "optionId": None,
                "path": (
                    "/assessments/" "976663c1-aa5e-4d3b-8455-9980fc3f26ca/dialog/next"
                ),
                "cardType": "TEXT",
                "description": (
                    "Welcome to the MomConnect Symptom "
                    "Checker in partnership with Ada. "
                    "Let's start with some questions about the symptoms. "
                    "Then, we will help you decide what to do next."
                ),
                "pdf_media_id": "",
                "title": "",
            },
            message,
        )

    @patch("ada.views.post_to_ada")
    def test_next_dialog(self, mock_post_to_ada):
        request = utils.build_rp_request(self.data_next_dialog)
        self.assertEqual(request, {"step": 5, "value": "27"})

        mock_post_to_ada.return_value = {
            "cardType": "CHOICE",
            "step": 6,
            "title": {"en-GB": "Patient Information"},
            "description": {"en-GB": "Are you pregnant?"},
            "explanations": [
                {
                    "label": {"en-GB": "What does this mean?"},
                    "text": {
                        "en-GB": (
                            "The status of a current pregnancy, "
                            "typically confirmed through a blood "
                            "or urine test."
                        )
                    },
                }
            ],
            "options": [
                {"optionId": 0, "text": {"en-GB": "Yes"}},
                {"optionId": 1, "text": {"en-GB": "No"}},
                {"optionId": 2, "text": {"en-GB": "I'm not sure"}},
            ],
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/7c7fd68f-c7be-4553-add6-49bfdce22979",
                },
                "next": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "7c7fd68f-c7be-4553-add6-49bfdce22979/dialog/next"
                    ),
                },
                "previous": {
                    "method": "POST",
                    "href": (
                        "/assessments/"
                        "7c7fd68f-c7be-4553-add6-49bfdce22979/dialog/previous"
                    ),
                },
                "abort": {
                    "method": "PUT",
                    "href": "/assessments/7c7fd68f-c7be-4553-add6-49bfdce22979/abort",
                },
            },
        }

        pdf = utils.pdf_ready(mock_post_to_ada.return_value)
        self.assertEqual(pdf, False)
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            self.entry_url, self.data_next_dialog, format="json"
        )
        self.assertRedirects(
            response,
            (
                "/api/v2/ada/nextdialog?"
                "contact_uuid=67460e74-02e3-11e8-b443"
                "-00163e990bdb&msisdn=27856454612&"
                "choiceContext=&choices=None&message="
                "How+old+are+you%3F%0A%0AReply+%2ABACK%2A+"
                "to+go+to+the+previous+question+or+%2AMENU%2A+"
                "to+end+the+assessment&explanations=&step=5&value="
                "27&optionId=None&path=%2Fassessments%2F"
                "f9d4be32-78fa-48e0-b9a3-e12e305e73ce%2Fdialog%2F"
                "next&cardType=INPUT&title=Patient+Information&"
                "description=How+old+are+you%3F&formatType=integer"
                "&max=120&max_error=Age+must+be+120+years+or+"
                "younger+to+assess+the+symptoms&min=1&min_error="
                "Age+in+years+must+be+greater+than+0+to+"
                "assess+the+symptoms"
            ),
        )

    @patch("ada.views.post_to_ada")
    def test_roadblock(self, mock_post_to_ada):
        request = utils.build_rp_request(self.data_next_dialog)
        self.assertEqual(request, {"step": 5, "value": "27"})

        mock_post_to_ada.return_value = {
            "cardType": "ROADBLOCK",
            "step": 28,
            "title": {"en-GB": "End of Assessment"},
            "description": {
                "en-GB": "MomConnect is here if you need immediate support"
            },
            "label": {"en-GB": "Return to MomConnect"},
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/1b2e19d9-1414-47d2-9d15-21e64fb0b357",
                }
            },
        }
        pdf = utils.pdf_ready(mock_post_to_ada.return_value)
        self.assertEqual(pdf, False)
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            self.entry_url, self.roadblock_dialog, format="json"
        )
        self.assertRedirects(
            response,
            (
                "/api/v2/ada/nextdialog?"
                "contact_uuid=67460e74-02e3-11e8-b443"
                "-00163e990bdb&msisdn=27856454612&"
                "choiceContext=&choices=None&message="
                "Are+you+sure+you+want+to+end%3F%0A%0AReply+%2ABACK%2A+"
                "to+go+to+the+previous+question+or+%2AMENU%2A+"
                "to+end+the+assessment&explanations=&step=25&value="
                "Yes&optionId=None&path=%2Fassessments%2F"
                "f9d4be32-78fa-48e0-b9a3-e12e305e73ce%2Fdialog%2F"
                "next&cardType=INPUT&title=Roadblock+warning&"
                "description=Roadblock+warning&formatType=string"
                "&max=None&max_error=&min=None&min_error="
            ),
        )
        message = utils.format_message(mock_post_to_ada.return_value)
        self.assertEqual(
            message,
            {
                "message": ("MomConnect is here if you " "need immediate support"),
                "explanations": "",
                "step": 28,
                "optionId": None,
                "path": ("/assessments/" "1b2e19d9-1414-47d2-9d15-21e64fb0b357"),
                "cardType": "ROADBLOCK",
                "description": ("MomConnect is here if you need " "immediate support"),
                "pdf_media_id": "",
                "title": "",
            },
            message,
        )


class AdaAssessmentReport(APITestCase):
    maxDiff = None
    data = {
        "contact_uuid": "67460e74-02e3-11e8-b443-00163e990bdd",
        "msisdn": "27856454612",
        "choiceContext": "",
        "choices": None,
        "message": (
            "How old are you?\n\nReply *BACK* to go to "
            "the previous question or *MENU* to "
            "end the assessment"
        ),
        "explanations": "",
        "step": 39,
        "value": "27",
        "optionId": None,
        "path": "/assessments/f9d4be32-78fa-48e0-b9a3-e12e305e73ce/dialog/next",
        "cardType": "INPUT",
        "title": "Patient Information",
        "description": "How old are you?",
        "formatType": "integer",
        "max": 120,
        "max_error": "Age must be 120 years or younger to assess the symptoms",
        "min": 1,
        "min_error": "Age in years must be greater than 0 to assess the symptoms",
        "pattern": "",
    }

    start_url = reverse("ada-assessments")
    next_dialog_url = reverse("ada-next-dialog")

    destination_url = (
        "/api/v2/ada/nextdialog?contact_uuid="
        "67460e74-02e3-11e8-b443-00163e990bdd&"
        "msisdn=27856454612&choiceContext=&"
        "choices=None&message=How+old+are+you%3F"
        "%0A%0AReply+%2ABACK%2A+to+go+to+the+"
        "previous+question+or+%2AMENU%2A+to+end"
        "+the+assessment&explanations=&step="
        "39&value=27&optionId=None&path=%2F"
        "assessments%2Ff9d4be32-78fa-48e0-b9a3"
        "-e12e305e73ce%2Fdialog%2Fnext&cardType"
        "=INPUT&title=Patient+Information&"
        "description=How+old+are+you%3F&formatType=integer"
        "&max=120&max_error=Age+must+be+120+years+or+younger"
        "+to+assess+the+symptoms&min=1&min_error=Age+in+"
        "years+must+be+greater+than+0+to+assess+the+symptoms"
    )

    pdf_url = (
        "/api/v2/ada/reports?payload=%7B%22cardType%22%3A"
        "%20%22REPORT%22%2C%20%22step%22%3A%2043%2C%20%22"
        "title%22%3A%20%7B%22en-GB%22%3A%20%22Results%22%"
        "7D%2C%20%22description%22%3A%20%7B%22en-GB%22%3A"
        "%20%22People%20with%20symptoms%20similar%20to%20"
        "yours%20do%20not%20usually%20require%20urgent%20"
        "medical%20care.%20You%20should%20seek%20advice%20"
        "from%20a%20doctor%20though%2C%20within%20the%20"
        "next%202-3%20days.%20If%20your%20symptoms%20get%20"
        "worse%2C%20or%20if%20you%20notice%20new%20symptoms"
        "%2C%20you%20may%20need%20to%20consult%20a%20doctor"
        "%20sooner.%22%7D%2C%20%22_links%22%3A%20%7B%22self"
        "%22%3A%20%7B%22method%22%3A%20%22GET%22%2C%20%22"
        "href%22%3A%20%22/assessments/5581bfeb-2803-4beb"
        "-b627-9f9d2a5651d8%22%7D%2C%20%22report%22%3A"
        "%20%7B%22method%22%3A%20%22GET%22%2C%20%22href"
        "%22%3A%20%22/reports/5581bfeb-2803-4beb-b627"
        "-9f9d2a5651d8%22%7D%2C%20%22abort%22%3A%20%7B"
        "%22method%22%3A%20%22PUT%22%2C%20%22href%22%3A"
        "%20%22/assessments/5581bfeb-2803-4beb-b627"
        "-9f9d2a5651d8/abort%22%7D%7D%2C+%22"
        "pdf_media_id%22%3A+%22media-uuid%22%7D"
    )

    pdf_data = {
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
        "pdf_media_id": "media-uuid",
        "title": "",
    }

    @patch("ada.views.upload_turn_media")
    @patch("ada.views.get_report")
    @patch("ada.views.pdf_ready")
    @patch("ada.views.post_to_ada")
    def test_assessment_report(
        self, mock_post_to_ada, mock_pdf_ready, mock_get_report, mock_upload_turn_media
    ):
        mock_post_to_ada.return_value = {
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

        mock_get_report.return_value = "pdf-content"
        mock_upload_turn_media.return_value = "media-uuid"
        mock_pdf_ready.return_value = utils.pdf_ready(mock_post_to_ada.return_value)
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.start_url, self.data, format="json")
        self.assertRedirects(response, self.destination_url, target_status_code=302)
        response = self.client.get(self.destination_url, format="json")
        self.assertRedirects(response, self.pdf_url, target_status_code=200)
        response = self.client.get(self.pdf_url, format="json")
        self.assertEqual(response.json(), self.pdf_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdaEDC(APITestCase):
    @patch("ada.views.upload_edc_media")
    @patch("ada.views.get_edc_report")
    def test_edc_submit_report(self, mock_get_edc_report, mock_upload_edc_media):
        mock_get_edc_report.return_value = {
            "caseName": "chronic schistosomiasis",
            "patient": {
                "name": "Chima",
                "age": {
                    "value": 28,
                    "unit": "a",
                    "entryTs": "2022-08-09T21:02:01.698Z",
                },
                "sex": "male",
            },
        }

        mock_upload_edc_media.return_value = "Successfully submitted to Castor"
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-edc-reports"),
            json.dumps(
                {
                    "contact_uuid": "bcffcc74-0d27-46a2-b165-60a07ef07878",
                    "report_id": "484c2534-422c-4381-97c4-2467222685",
                    "study_id": "22BBDE33-D35A-44B6-A759-CE742FCEF5A5",
                    "record_id": "483390-00001-0001",
                    "field_id": "11AC8D74-DBB6-5FF7-AFW3-1731A9D72E90",
                    "token": "880b00a7b8f230d4c9a7281a0a2530ca52fb6c13b",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.json(), "Successfully submitted to Castor")
