import json
from unittest.mock import patch
from urllib.parse import urljoin

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ada import utils

from .models import AdaAssessment, RedirectUrl


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
    def test_successful_flow_start(self, mock_start_rapidpro_flow):
        whatsappid = "12345"

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
            reverse("ada-start-assessment"),
            json.dumps(
                {
                    "message": (
                        "Please type in the symptom that is troubling you, "
                        "only one symptom at a time. Reply back to go to the "
                        "previous question or abort to end the assessment"
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
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(
            response.json(),
            {
                "message": (
                    "Please type in the symptom that is troubling you, "
                    "only one symptom at a time. Reply back to go to the "
                    "previous question or abort to end the assessment"
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
                "error": (
                    "We are sorry, your reply should be between "
                    "1 and 100 characters. Please try again."
                ),
            },
            response.json(),
        )

    # Return validation error for invalid choice for CHOICE cardType
    def test_choice_type(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-start-assessment"),
            json.dumps(
                {
                    "choices": 3,
                    "message": (
                        "What is the issue?\n\nAbdominal pain\n"
                        "Headache"
                        "\nNone of these\n\nChoose the option that matches "
                        "your answer. "
                        "Eg, 1 for Abdominal pain\n\nEnter *back* to go "
                        "to the previous question or *abort* "
                        "to end the assessment"
                    ),
                    "step": 4,
                    "value": 9,
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
                "choices": "3",
                "message": (
                    "What is the issue?\n\nAbdominal pain\nHeadache"
                    "\nNone of these\n\nChoose the option that "
                    "matches your answer. "
                    "Eg, 1 for Abdominal pain\n\nEnter *back* to go "
                    "to the previous question or *abort* "
                    "to end the assessment"
                ),
                "step": "4",
                "value": "9",
                "optionId": "0",
                "path": "/assessments/assessment-id/dialog/next",
                "cardType": "CHOICE",
                "title": "SYMPTOM",
                "error": (
                    "Something seems to have gone wrong. "
                    "You entered 9 but there are only 3 options."
                ),
            },
            response,
        )


class AdaReportViewTests(APITestCase):
    report_reponse = {"pdf sent"}

    @patch.object(AdaAssessment, "save")
    @patch("ada.utils.get_report", return_value=report_reponse)
    @patch("ada.utils.post_to_ada")
    @patch("ada.utils.get_rp_payload")
    def test_choice_type_valid(
        self, mock_get_rp_payload, mock_post_response, mock_get_report, mock_save_mock
    ):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("ada-start-assessment"),
            json.dumps(
                {
                    "contact_uuid": "49548747-48888043",
                    "choices": 3,
                    "message": (
                        "What is the issue?\n\nAbdominal pain"
                        "\nHeadache\nNone of these\n\n"
                        "Choose the option that matches your answer. "
                        "Eg, 1 for Abdominal pain\n\nEnter *back* to go to "
                        "the previous question or *abort* to "
                        "end the assessment"
                    ),
                    "step": 6,
                    "value": 2,
                    "optionId": 0,
                    "path": "/assessments/assessment-id/dialog/next",
                    "cardType": "CHOICE",
                    "title": "SYMPTOM",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response)

        mock_post_response.return_value = {
            "cardType": "CHOICE",
            "step": 40,
            "title": {"en-US": "YOUR REPORT"},
            "description": {"en-US": ""},
            "options": [
                {"optionId": 0, "text": {"en-US": "Ask momconnect"}},
                {"optionId": 1, "text": {"en-US": "Phone a nurse"}},
                {"optionId": 2, "text": {"en-US": "Download full report"}},
            ],
            "_links": {
                "self": {
                    "method": "GET",
                    "href": "/assessments/898d915e-229f-48f2-9b98-cfd760ba8965",
                },
                "report": {
                    "method": "GET",
                    "href": "/reports/17340f51604cb35bd2c6b7b9b16f3aec",
                },
            },
        }
        response = utils.get_message(mock_get_rp_payload.return_value)
        self.assertEqual(response, mock_get_report.return_value, response)
