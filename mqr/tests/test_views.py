import datetime
import json
import uuid
from unittest.mock import patch

import responses
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from temba_client.v2 import TembaClient

from mqr import utils, views
from mqr.models import BaselineSurveyResult, MqrStrata
from registrations.models import ClinicCode


class NextMessageViewTests(APITestCase):
    url = reverse("mqr-nextmessage")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "arm": ["This field is required."],
                "edd_or_dob_date": ["This field is required."],
                "subscription_type": ["This field is required."],
                "mom_name": ["This field is required."],
                "contact_uuid": ["This field is required."],
                "run_uuid": ["This field is required."],
            },
        )

    @patch("mqr.views.get_next_message")
    def test_next_message(self, mock_get_next_message):
        contact_uuid = str(uuid.uuid4())
        run_uuid = str(uuid.uuid4())

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_next_message.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message 1",
            "next_send_date": "2022-03-14",
            "tag": "BCM_week_PRE19",
        }

        response = self.client.post(
            self.url,
            {
                "arm": "BCM",
                "edd_or_dob_date": "2022-07-12",
                "subscription_type": "PRE",
                "mom_name": "Test",
                "contact_uuid": contact_uuid,
                "run_uuid": run_uuid,
                "sequence": "",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "message": "Test Message 1",
                "is_template": False,
                "has_parameters": False,
                "next_send_date": "2022-03-14",
                "tag": "BCM_week_PRE19",
            },
        )

        mock_tracking_data = {
            "data__contact_uuid": contact_uuid,
            "data__run_uuid": run_uuid,
            "data__mqr": "scheduled",
        }

        mock_get_next_message.assert_called_with(
            datetime.date(2022, 7, 12),
            "PRE",
            "BCM",
            None,
            "",
            "Test",
            mock_tracking_data,
        )

    @patch("mqr.views.get_next_message")
    def test_next_message_error(self, mock_get_next_message):
        contact_uuid = str(uuid.uuid4())
        run_uuid = str(uuid.uuid4())

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_next_message.return_value = {"error": "no message found"}

        response = self.client.post(
            self.url,
            {
                "arm": "BCM",
                "edd_or_dob_date": "2022-07-12",
                "subscription_type": "PRE",
                "mom_name": "Test",
                "contact_uuid": contact_uuid,
                "run_uuid": run_uuid,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"error": "no message found"},
        )


class FaqViewTests(APITestCase):
    url = reverse("mqr-faq")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "tag": ["This field is required."],
                "faq_number": ["This field is required."],
                "contact_uuid": ["This field is required."],
                "run_uuid": ["This field is required."],
            },
        )

    @patch("mqr.views.get_faq_message")
    def test_faq_message(self, mock_get_faq_message):
        contact_uuid = str(uuid.uuid4())
        run_uuid = str(uuid.uuid4())

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_faq_message.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message 1",
        }

        response = self.client.post(
            self.url,
            {
                "tag": "BCM_week_pre22",
                "faq_number": 1,
                "viewed": ["test"],
                "contact_uuid": contact_uuid,
                "run_uuid": run_uuid,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "message": "Test Message 1",
                "is_template": False,
                "has_parameters": False,
            },
        )

        mock_tracking_data = {
            "data__contact_uuid": contact_uuid,
            "data__run_uuid": run_uuid,
            "data__mqr": "faq",
        }

        mock_get_faq_message.assert_called_with(
            "bcm_week_pre22", 1, ["test"], mock_tracking_data
        )


class FaqMenuViewTests(APITestCase):
    url = reverse("mqr-faq-menu")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"tag": ["This field is required."]},
        )

    @patch("mqr.views.get_faq_menu")
    def test_faq_menu(self, mock_get_faq_menu):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_faq_menu.return_value = ("2 - menu1, 3 - Menu2", "1,2")

        response = self.client.post(
            self.url,
            {"tag": "RCM_BCM_week_pre22", "menu_offset": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "menu": "2 - menu1, 3 - Menu2",
                "faq_numbers": "1,2",
            },
        )

        mock_get_faq_menu.assert_called_with("rcm_week_pre22", [], False, 1)


def override_get_today():
    return datetime.datetime.strptime("20220308", "%Y%m%d").date()


class StrataRandomization(APITestCase):
    def setUp(self):
        utils.get_today = override_get_today

    url = reverse("mqr_randomstrataarm")

    def test_random_arm_unauthorized_user(self):
        """
        unauthorized user access denied
        Returns: status code 401

        """

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_random_arm(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        ClinicCode.objects.create(
            code="123456", value=1, uid=1, name="test", province="EC"
        )

        response = self.client.post(
            self.url,
            data={
                "facility_code": "123456",
                "estimated_delivery_date": datetime.date(2022, 8, 17),
                "mom_age": 32,
            },
            format="json",
        )

        strata_arm = MqrStrata.objects.get(
            province="EC", weeks_pregnant_bucket="16-20", age_bucket="31+"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, strata_arm.order.split(",")[0])
        self.assertEqual(strata_arm.next_index, 1)

    def test_random_arm_exclude(self):
        """
        Exclude if person doesn't qualify for study
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        ClinicCode.objects.create(
            code="123456", value=1, uid=1, name="test", province="EC"
        )

        response = self.client.post(
            self.url,
            data={
                "estimated_delivery_date": "2022-01-30",
                "facility_code": "123456",
                "mom_age": "38",
            },
            format="json",
        )

        self.assertEqual(
            response.json(),
            {"Excluded": True, "reason": "clinic: 123456, weeks: None, age: 38"},
        )

    @override_settings(MQR_STUDY_START_DATE="2022-01-03")
    def test_random_arm_exclude_study_limit(self):
        """
        Exclude if person doesn't qualify for study based on min study pregnancy weeks
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        ClinicCode.objects.create(
            code="123456", value=1, uid=1, name="test", province="EC"
        )

        response = self.client.post(
            self.url,
            data={
                "facility_code": "123456",
                "estimated_delivery_date": datetime.date(2022, 8, 17),
                "mom_age": 32,
            },
            format="json",
        )

        self.assertEqual(
            response.json(),
            {"Excluded": True, "reason": "study not active for weeks pregnant"},
        )

    def test_get_random_starta_arm(self):
        """
        Check the next arm from the existing data
        Returns: string response

        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        ClinicCode.objects.create(
            code="246800", value=2, uid=2, name="test", province="MP"
        )

        MqrStrata.objects.create(
            province="MP",
            weeks_pregnant_bucket="26-30",
            age_bucket="31+",
            next_index=1,
            order="ARM,RCM_BCM,RCM,RCM_SMS,BCM",
        )

        response = self.client.post(
            self.url,
            data={
                "facility_code": "246800",
                "estimated_delivery_date": datetime.date(2022, 6, 13),
                "mom_age": 34,
            },
            format="json",
        )

        self.assertEqual(response.data, {"random_arm": "RCM_BCM"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_out_of_index_arm(self):
        """
        Test for out of index to delete the order after maximum arm
        """

        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        ClinicCode.objects.create(
            code="369120", value=3, uid=3, name="test", province="FS"
        )

        MqrStrata.objects.create(
            province="FS",
            weeks_pregnant_bucket="26-30",
            age_bucket="18-30",
            next_index=4,
            order="ARM,RCM,RCM_SMS,BCM,RCM_BCM",
        )

        # This api call will delete the existing arm
        response = self.client.post(
            self.url,
            data={
                "facility_code": "369120",
                "estimated_delivery_date": datetime.date(2022, 6, 13),
                "mom_age": 22,
            },
            format="json",
        )

        strata_arm = MqrStrata.objects.filter(
            province="FS", weeks_pregnant_bucket="26-30", age_bucket="18-30"
        )

        self.assertEqual(strata_arm.count(), 0)
        self.assertEqual(response.data.get("random_arm"), "RCM_BCM")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BaselineSurveyResultViewTests(APITestCase):
    url = reverse("baselinesurveyresult-list")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"msisdn": ["This field is required."]},
        )

    def test_successful_create(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        data = {
            "msisdn": "27831231234",
            "breastfeed": BaselineSurveyResult.YesNoSkip.YES,
            "breastfeed_period": BaselineSurveyResult.BreastfeedPeriod.MONTHS_0_3,
            "vaccine_importance": BaselineSurveyResult.AgreeDisagree.AGREE,
            "vaccine_benefits": BaselineSurveyResult.AgreeDisagree.DISAGREE,
            "clinic_visit_frequency": BaselineSurveyResult.ClinicVisitFrequency.NEVER,
            "vegetables": BaselineSurveyResult.YesNoSkip.SKIP,
            "fruit": BaselineSurveyResult.YesNoSkip.NO,
            "dairy": BaselineSurveyResult.YesNoSkip.SKIP,
            "liver_frequency": BaselineSurveyResult.LiverFrequency.LESS_ONCE_MONTH,
            "danger_sign1": BaselineSurveyResult.DangerSign1.WEIGHT_GAIN,
            "danger_sign2": BaselineSurveyResult.DangerSign2.BLOAT,
            "marital_status": BaselineSurveyResult.MaritalStatus.MARRIED,
            "education_level": BaselineSurveyResult.EducationLevel.DEGREE_OR_HIGHER,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertIsNotNone(data.pop("created_at"))
        self.assertIsNotNone(data.pop("updated_at"))
        self.assertIsNone(data.pop("airtime_sent_at"))
        self.assertEqual(
            data,
            {
                "msisdn": "27831231234",
                "created_by": "test",
                "breastfeed": "yes",
                "breastfeed_period": "0_3_months",
                "vaccine_importance": "agree",
                "vaccine_benefits": "disagree",
                "clinic_visit_frequency": "never",
                "vegetables": "skip",
                "fruit": "no",
                "dairy": "skip",
                "liver_frequency": "less_once_a_month",
                "danger_sign1": "weight_gain",
                "danger_sign2": "bloating",
                "marital_status": "married",
                "education_level": "degree_or_higher",
                "airtime_sent": False,
            },
        )

    def test_successful_update(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        msisdn = "27831231234"
        result = BaselineSurveyResult.objects.create(
            **{
                "msisdn": msisdn,
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )

        url = reverse("baselinesurveyresult-detail", args=(msisdn,))
        response = self.client.patch(
            url,
            {
                "breastfeed": BaselineSurveyResult.YesNoSkip.YES,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result.refresh_from_db()

        self.assertEqual(response.json()["msisdn"], result.msisdn)
        self.assertEqual(result.breastfeed, BaselineSurveyResult.YesNoSkip.YES)
        self.assertIsNone(result.airtime_sent_at)

    def test_successful_update_airtime(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        msisdn = "27831231234"
        result = BaselineSurveyResult.objects.create(
            **{
                "msisdn": msisdn,
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )

        url = reverse("baselinesurveyresult-detail", args=(msisdn,))
        response = self.client.patch(
            url,
            {
                "airtime_sent": True,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result.refresh_from_db()

        self.assertEqual(response.json()["msisdn"], result.msisdn)
        self.assertTrue(result.airtime_sent)
        self.assertIsNotNone(result.airtime_sent_at)

    def test_get_result_by_msisdn(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        msisdn = "27831231234"

        BaselineSurveyResult.objects.create(
            **{
                "msisdn": msisdn,
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )
        BaselineSurveyResult.objects.create(
            **{
                "msisdn": "27831112222",
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )

        response = self.client.get(
            self.url,
            params={"msisdn": msisdn},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result = response.json()["results"][0]
        self.assertEqual(result["msisdn"], msisdn)

    def test_get_result_by_msisdn_not_found(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.get(
            self.url,
            params={"msisdn": "27831231234"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)


class FirstSendDateViewTests(APITestCase):
    url = reverse("mqr-firstsenddate")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_data(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"edd_or_dob_date": ["This field is required."]},
        )

    @patch("mqr.views.get_first_send_date")
    def test_faq_message(self, mock_get_first_send_date):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        mock_get_first_send_date.return_value = datetime.date(2022, 7, 15)

        response = self.client.post(
            self.url,
            {
                "edd_or_dob_date": "2022-07-12",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "first_send_date": "2022-07-15",
            },
        )

        mock_get_first_send_date.assert_called_with(datetime.date(2022, 7, 12))


class MqrEndlineChecksViewSetTests(APITestCase):
    url = reverse("mqr-endlinechecks")

    def setUp(self):
        """
        Helper function to create RapidPro connection instance
        """
        views.rapidpro = TembaClient("textit.in", "test-token")

    def add_get_rapidpro_contact(
        self, consent="Accepted", arm="RCM_BCM", received=None, optedout=None
    ):
        """
        Helper function to build mock responses
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp%3A27831231234",
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "uuid": "148947f5-a3b6-4b6b-9e9b-25058b1b7800",
                        "name": "",
                        "language": "eng",
                        "groups": [],
                        "fields": {
                            "mqr_consent": consent,
                            "mqr_arm": arm,
                            "endline_airtime_received": received,
                            "opted_out": optedout,
                        },
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27712345682"],
                    }
                ],
            },
        )

    @responses.activate
    def test_mqr_endline_missing_msisdn(self):
        """
        Check for an missing msisdn number
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"msisdn": ["This field is required."]})

    @responses.activate
    def test_mqr_endline_invalid_msisdn(self):
        """
        Check for an invalid msisdn number
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.post(self.url, {"msisdn": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"msisdn": ["(1) The string supplied did not seem to be a phone number."]},
        )

    @responses.activate
    def test_mqr_endline_get_contact_not_found(self):
        """
        Check that the contact exists
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27831231234",
            json={"next": None, "previous": None, "results": []},
        )
        response = self.client.post(self.url, data={"msisdn": "27831231234"})
        self.assertEqual(response.status_code, 404)

    @responses.activate
    def test_mqr_endline_get_contact_no_arm_found(self):
        """
        Check that the contact exists
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        self.add_get_rapidpro_contact(arm="")
        response = self.client.post(self.url, data={"msisdn": "27831231234"})
        self.assertEqual(response.status_code, 404)

    @responses.activate
    def test_mqr_endline_airtime_already_received(self):
        """
        Check that the contact has not already received the airtime
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        self.add_get_rapidpro_contact(received="TRUE")
        response = self.client.post(self.url, data={"msisdn": "27831231234"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Airtime already received"})

    @responses.activate
    def test_mqr_endline_validate_start_flow(self):
        """
        Check that we can start the flow
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        self.add_get_rapidpro_contact()

        responses.add(
            responses.POST,
            "https://textit.in/api/v2/flow_starts.json",
            json={
                "uuid": "mqr-send-airtime-flow-uuid",
                "flow": {
                    "uuid": "mqr-send-airtime-flow-uuid",
                    "name": "MQR sent endline airtime",
                },
                "groups": [],
                "contacts": [],
                "extra": {},
                "restart_participants": True,
                "status": "complete",
                "created_on": datetime.datetime.now().isoformat(),
                "modified_on": datetime.datetime.now().isoformat(),
            },
        )

        response = self.client.post(self.url, data={"msisdn": "27831231234"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(), {"uuid": "148947f5-a3b6-4b6b-9e9b-25058b1b7800"}
        )

        request = responses.calls[1]
        self.assertEqual(
            json.loads(request.request.body),
            {
                "flow": "mqr-send-airtime-flow-uuid",
                "urns": ["whatsapp:27831231234"],
                "extra": {},
            },
        )
