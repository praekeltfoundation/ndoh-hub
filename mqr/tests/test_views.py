import datetime
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mqr.models import BaselineSurveyResult, MqrStrata
from ndoh_hub import utils
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
            datetime.date(2022, 7, 12), "PRE", "BCM", "", "Test", mock_tracking_data
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
    return datetime.datetime.strptime("20200308", "%Y%m%d").date()


class StrataRandomization(APITestCase):
    def setUp(self):
        utils.get_today = override_get_today()

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
            "vaccine_benifits": BaselineSurveyResult.AgreeDisagree.DISAGREE,
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
                "id": 1,
                "msisdn": "27831231234",
                "created_by": "test",
                "breastfeed": "yes",
                "breastfeed_period": "0_3_months",
                "vaccine_importance": "agree",
                "vaccine_benifits": "disagree",
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

        result = BaselineSurveyResult.objects.create(
            **{
                "msisdn": "27831231234",
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )

        response = self.client.post(
            self.url,
            {
                "msisdn": "27831231234",
                "breastfeed": BaselineSurveyResult.YesNoSkip.YES,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result.refresh_from_db()

        self.assertEqual(response.json()["id"], result.id)
        self.assertEqual(result.breastfeed, BaselineSurveyResult.YesNoSkip.YES)
        self.assertIsNone(result.airtime_sent_at)

    def test_successful_update_airtime(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        result = BaselineSurveyResult.objects.create(
            **{
                "msisdn": "27831231234",
                "breastfeed": BaselineSurveyResult.YesNoSkip.SKIP,
            }
        )

        response = self.client.post(
            self.url,
            {
                "msisdn": "27831231234",
                "airtime_sent": True,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result.refresh_from_db()

        self.assertEqual(response.json()["id"], result.id)
        self.assertTrue(result.airtime_sent)
        self.assertIsNotNone(result.airtime_sent_at)
