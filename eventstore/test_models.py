from unittest.mock import call, patch

from django.test import TestCase, override_settings

from eventstore.models import (
    Covid19Triage, Event, HealthCheckUserProfile, Message,HCSStudyBRandomization)


class MessageTests(TestCase):
    def test_is_operator_message(self):
        """
        Whether this message is from an operator or not
        """
        msg = Message(
            message_direction=Message.OUTBOUND,
            type="text",
            data={
                "_vnd": {
                    "v1": {
                        "author": {"type": "OPERATOR"},
                        "chat": {"owner": "27820001001"},
                    }
                }
            },
        )
        self.assertEqual(msg.is_operator_message, True)
        msg.data = {}
        self.assertEqual(msg.is_operator_message, False)

    def test_has_label(self):
        """
        Test if a message contains a label
        """
        msg = Message(
            message_direction=Message.OUTBOUND,
            type="text",
            data={"_vnd": {"v1": {"labels": [{"value": "Label1", "id": "label-id"}]}}},
        )
        self.assertTrue(msg.has_label("Label1"))
        self.assertFalse(msg.has_label("Label2"))

        msg.fallback_channel = True
        self.assertFalse(msg.has_label("Label1"))

        msg.data = {}
        msg.fallback_channel = False
        self.assertFalse(msg.has_label("Label1"))


class EventTests(TestCase):
    def test_is_hsm_error(self):
        """
        Is this event a hsm error
        """
        event = Event(
            fallback_channel=False,
            data={"errors": [{"title": "structure unavailable"}]},
        )
        self.assertTrue(event.is_hsm_error)

        event.data = {"errors": [{"title": "envelope mismatch"}]}
        self.assertTrue(event.is_hsm_error)

        event.data = {"errors": [{"title": "something else"}]}
        self.assertFalse(event.is_hsm_error)

        event.fallback_channel = True
        event.data = {"errors": [{"title": "envelope mismatch"}]}
        self.assertFalse(event.is_hsm_error)

        event.fallback_channel = False
        event.data = {}
        self.assertFalse(event.is_hsm_error)

    def test_is_message_expired_error(self):
        """
        Is this event a message expired error
        """
        event = Event(fallback_channel=False, data={"errors": [{"code": 410}]})
        self.assertTrue(event.is_message_expired_error)

        event = Event(fallback_channel=False, data={"errors": [{"code": 111}]})
        self.assertFalse(event.is_message_expired_error)

        event = Event(fallback_channel=True, data={"errors": [{"code": 410}]})
        self.assertFalse(event.is_message_expired_error)

        event = Event(fallback_channel=False, data={})
        self.assertFalse(event.is_message_expired_error)

    def test_is_whatsapp_failed_delivery(self):
        """
        Is this event a message expired error
        """
        event = Event(fallback_channel=False, status="failed")
        self.assertTrue(event.is_whatsapp_failed_delivery_event)

        event = Event(fallback_channel=False, status="sent")
        self.assertFalse(event.is_whatsapp_failed_delivery_event)

        event = Event(fallback_channel=True, status="failed")
        self.assertFalse(event.is_whatsapp_failed_delivery_event)


class HealthCheckUserProfileTests(TestCase):
    def test_update_from_healthcheck(self):
        """
        Updates the correct fields from the healthcheck
        """
        healthcheck = Covid19Triage(
            msisdn="+27820001001",
            first_name="first",
            last_name=None,
            data={"donotreplace": "", "replaceint": 0, "replacebool": False},
        )
        profile = HealthCheckUserProfile(
            first_name="oldfirst",
            last_name="old_last",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )
        profile.update_from_healthcheck(healthcheck)
        self.assertEqual(profile.first_name, "first")
        self.assertEqual(profile.last_name, "old_last")
        self.assertEqual(
            profile.data,
            {
                "donotreplace": "value",
                "replaceint": 0,
                "replacebool": False,
                "existing": "value",
            },
        )

    def test_get_or_prefill_existing(self):
        """
        Returns existing profile
        """
        profile = HealthCheckUserProfile.objects.create(msisdn="+27820001001")
        fetched_profile = HealthCheckUserProfile.objects.get_or_prefill("+27820001001")
        self.assertEqual(profile.msisdn, fetched_profile.msisdn)

    def test_get_or_prefill_no_values(self):
        """
        Should return an empty profile if there are matching profiles, and no data to
        prefill with
        """
        profile = HealthCheckUserProfile.objects.get_or_prefill("+27820001001")
        self.assertEqual(profile.msisdn, "")

    def test_get_or_prefill_existing_healthchecks(self):
        """
        If no profile exists, and there are existing healthchecks, should use those to
        prefill the profile
        """
        Covid19Triage.objects.create(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="oldlast",
            fever=False,
            cough=False,
            sore_throat=False,
            tracing=True,
        )
        Covid19Triage.objects.create(
            msisdn="+27820001001",
            last_name="newlast",
            fever=False,
            cough=False,
            sore_throat=False,
            tracing=True,
            preexisting_condition="no",
        )
        profile = HealthCheckUserProfile.objects.get_or_prefill("+27820001001")
        self.assertEqual(profile.first_name, "oldfirst")
        self.assertEqual(profile.last_name, "newlast")
        self.assertEqual(profile.preexisting_condition, "no")

    def test_get_study_totals_per_province(self):
        HealthCheckUserProfile.objects.create(
            msisdn="+27820001001",
            province="ZA-WC",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
        )
        profile_wc = HealthCheckUserProfile.objects.create(
            msisdn="+27820001002",
            province="ZA-WC",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
        )
        profile_ec = HealthCheckUserProfile.objects.create(
            msisdn="+27820001003",
            province="ZA-EC",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
        )

        total, percentage = profile_wc.get_study_totals_per_province()
        self.assertEqual(total, 2)
        self.assertEqual(int(percentage), 66)

        total, percentage = profile_ec.get_study_totals_per_province()
        self.assertEqual(total, 1)
        self.assertEqual(int(percentage), 33)

    @patch("eventstore.models.HealthCheckUserProfile.get_study_totals_per_province")
    def test_get_random_study_arm(self, mock_get_study_totals_per_province):
        profile = HealthCheckUserProfile(msisdn="+27820001001", province="ZA-WC")

        mock_get_study_totals_per_province.return_value = (500, 9)
        self.assertIsNotNone(profile.get_random_study_arm())

        mock_get_study_totals_per_province.return_value = (5000, 30)
        self.assertIsNone(profile.get_random_study_arm())

    @patch("eventstore.models.update_turn_contact")
    def test_update_post_screening_study_arms_a_whatsapp(
        self, mock_update_turn_contact
    ):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            hcs_study_c_testing_arm=HealthCheckUserProfile.ARM_CONTROL,
            province="ZA-WC",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_LOW, "whatsapp_healthcheck"
        )

        self.assertIsNotNone(profile.hcs_study_a_arm)

        mock_update_turn_contact.delay.assert_has_calls(
            [call("+27820001001", "hcs_study_a_arm", profile.hcs_study_a_arm)]
        )

    @patch("eventstore.models.update_turn_contact")
    def test_update_post_screening_study_arms_a_ussd(self, mock_update_turn_contact):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            age=Covid19Triage.AGE_18T40,
            province="ZA-WC",
            hcs_study_c_testing_arm=HealthCheckUserProfile.ARM_CONTROL,
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(Covid19Triage.RISK_LOW, "USSD")

        self.assertIsNone(profile.hcs_study_a_arm)

        mock_update_turn_contact.delay.assert_not_called()

    @patch("eventstore.models.update_turn_contact")
    def test_update_post_screening_study_arms_c_low(self, mock_update_turn_contact):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
            age=Covid19Triage.AGE_18T40,
            province="ZA-WC",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_LOW, "whatsapp_healthcheck"
        )

        self.assertIsNone(profile.hcs_study_c_testing_arm)
        self.assertIsNone(profile.hcs_study_c_quarantine_arm)

        mock_update_turn_contact.delay.assert_not_called()

    @patch("eventstore.models.start_study_c_registration_flow")
    @patch("eventstore.models.update_turn_contact")
    @override_settings(HCS_STUDY_C_REGISTRATION_FLOW_ID="123")
    def test_update_post_screening_study_arms_c_moderate(
        self, mock_update_turn_contact, mock_start_study_c_registration_flow
    ):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            province="ZA-WC",
            age=Covid19Triage.AGE_18T40,
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_MODERATE, "whatsapp_healthcheck"
        )

        self.assertIsNone(profile.hcs_study_c_testing_arm)
        self.assertIsNotNone(profile.hcs_study_c_quarantine_arm)

        mock_update_turn_contact.delay.assert_has_calls(
            [
                call(
                    "+27820001001",
                    "hcs_study_c_quarantine_arm",
                    profile.hcs_study_c_quarantine_arm,
                )
            ]
        )

        mock_start_study_c_registration_flow.delay.assert_called_with(
            "+27820001001",
            profile.hcs_study_c_testing_arm,
            profile.hcs_study_c_quarantine_arm,
            Covid19Triage.RISK_MODERATE,
            "whatsapp_healthcheck",
        )

    @patch("eventstore.models.start_study_c_registration_flow")
    @patch("eventstore.models.update_turn_contact")
    @override_settings(HCS_STUDY_C_REGISTRATION_FLOW_ID="123")
    def test_update_post_screening_study_arms_c_high(
        self, mock_update_turn_contact, mock_start_study_c_registration_flow
    ):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
            province="ZA-WC",
            age=Covid19Triage.AGE_18T40,
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_HIGH, "whatsapp_healthcheck"
        )

        self.assertIsNotNone(profile.hcs_study_c_testing_arm)
        self.assertIsNone(profile.hcs_study_c_quarantine_arm)

        mock_update_turn_contact.delay.assert_has_calls(
            [call("+27820001001", "hcs_study_c_arm", profile.hcs_study_c_testing_arm)]
        )

        mock_start_study_c_registration_flow.delay.assert_called_with(
            "+27820001001",
            profile.hcs_study_c_testing_arm,
            profile.hcs_study_c_quarantine_arm,
            Covid19Triage.RISK_HIGH,
            "whatsapp_healthcheck",
        )

    @patch("eventstore.models.update_turn_contact")
    def test_update_post_screening_study_arms_populated(self, mock_update_turn_contact):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            age=Covid19Triage.AGE_18T40,
            province="ZA-WC",
            hcs_study_a_arm=HealthCheckUserProfile.ARM_CONTROL,
            hcs_study_c_testing_arm=HealthCheckUserProfile.ARM_CONTROL,
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_HIGH, "whatsapp_healthcheck"
        )

        mock_update_turn_contact.delay.assert_not_called()

    @patch("eventstore.models.update_turn_contact")
    def test_update_post_screening_study_arms_under_age(self, mock_update_turn_contact):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            first_name="oldfirst",
            last_name="old_last",
            age=Covid19Triage.AGE_U18,
            province="ZA-WC",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_MODERATE, "whatsapp_healthcheck"
        )

        self.assertIsNone(profile.hcs_study_a_arm)
        self.assertIsNone(profile.hcs_study_c_testing_arm)
        self.assertIsNone(profile.hcs_study_c_quarantine_arm)

        mock_update_turn_contact.delay.assert_not_called()

    @patch("eventstore.models.update_turn_contact")
    @override_settings(HCS_STUDY_A_ACTIVE=False, HCS_STUDY_C_ACTIVE=False)
    def test_update_post_screening_study_arms_deactivated(
        self, mock_update_turn_contact
    ):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            age=Covid19Triage.AGE_18T40,
            province="ZA-WC",
            first_name="oldfirst",
            last_name="old_last",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_MODERATE, "whatsapp_healthcheck"
        )

        self.assertIsNone(profile.hcs_study_a_arm)
        self.assertIsNone(profile.hcs_study_c_testing_arm)
        self.assertIsNone(profile.hcs_study_c_quarantine_arm)

        mock_update_turn_contact.delay.assert_not_called()

    @patch("eventstore.models.update_turn_contact")
    @override_settings(
        HCS_STUDY_A_ACTIVE=False,
        HCS_STUDY_C_ACTIVE=False,
        HCS_STUDY_A_WHITELIST=["+27820001001"],
    )
    def test_update_post_screening_study_arms_whitelist(self, mock_update_turn_contact):
        profile = HealthCheckUserProfile(
            msisdn="+27820001001",
            age=Covid19Triage.AGE_18T40,
            province="ZA-WC",
            first_name="oldfirst",
            last_name="old_last",
            data={
                "donotreplace": "value",
                "replaceint": 1,
                "replacebool": True,
                "existing": "value",
            },
        )

        profile.update_post_screening_study_arms(
            Covid19Triage.RISK_MODERATE, "whatsapp_healthcheck"
        )

        self.assertIsNotNone(profile.hcs_study_a_arm)

        mock_update_turn_contact.delay.assert_called()


class HCSStudyBRandomizationTests(TestCase):
    @override_settings(
        HCS_STUDY_B_ACTIVE=True,
        HCS_STUDY_B_WHITELIST=["+27820001001"],
        HCS_STUDY_B_CREATED_BY=["sometokenuser"]
    )
    def test_create_study_b_arm_when_active(self):
        study = HCSStudyBRandomization(
            msisdn="+27820001001",
            province="ZA-WC",
            created_by="sometokenuser",
            source="WhatsApp"
        )

        study.process_study_b()

        self.assertIsNotNone(study.study_b_arm)
