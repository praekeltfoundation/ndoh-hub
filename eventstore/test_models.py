from django.test import TestCase

from eventstore.models import Covid19Triage, Event, HealthCheckUserProfile, Message


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
        )
        profile = HealthCheckUserProfile.objects.get_or_prefill("+27820001001")
        self.assertEqual(profile.first_name, "oldfirst")
        self.assertEqual(profile.last_name, "newlast")
