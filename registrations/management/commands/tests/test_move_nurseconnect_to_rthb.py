from io import StringIO
import json
from django.core.management import call_command
from django.test import TestCase
import responses

from ndoh_hub import utils_tests
from registrations.models import SubscriptionRequest


class MoveNurseConnectToRTHBTests(TestCase):
    @responses.activate
    def test_switch_subscription(self):
        """
        For each active nurseconnect subscription, it should be deactivated and
        a new one created
        """
        utils_tests.mock_get_messageset_by_shortname("nurseconnect_rthb.hw_full.1")
        utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_nurseconnect_rthb.hw_full.1"
        )
        utils_tests.mock_get_subscriptions(
            "?active=True&messageset_contains=nurseconnect",
            [
                {
                    "id": "subscription-uuid",
                    "identity": "identity-uuid",
                    "messageset": 61,
                    "next_sequence_number": 1,
                    "lang": "eng_ZA",
                    "active": True,
                }
            ],
        )
        utils_tests.mock_get_messageset(61)
        utils_tests.mock_update_subscription("subscription-uuid")

        out = StringIO()
        call_command("move_nurseconnect_to_rthb", stdout=out)

        self.assertIn("Switching subscription for identity-uuid", out.getvalue())
        [subreq] = SubscriptionRequest.objects.all()
        self.assertEqual(subreq.messageset, 63)
        self.assertEqual(subreq.schedule, 163)
        deactivation = responses.calls[-1]
        self.assertEqual(json.loads(deactivation.request.body), {"active": False})

    @responses.activate
    def test_switch_subscription_whatsapp(self):
        """
        If the current subscription is for whatsapp, the new subscription
        should also be for whatsapp.
        """
        utils_tests.mock_get_messageset_by_shortname("nurseconnect_rthb.hw_full.1")
        utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_nurseconnect_rthb.hw_full.1"
        )
        utils_tests.mock_get_subscriptions(
            "?active=True&messageset_contains=nurseconnect",
            [
                {
                    "id": "subscription-uuid",
                    "identity": "identity-uuid",
                    "messageset": 62,
                    "next_sequence_number": 1,
                    "lang": "eng_ZA",
                    "active": True,
                }
            ],
        )
        utils_tests.mock_get_messageset(62)
        utils_tests.mock_update_subscription("subscription-uuid")

        out = StringIO()
        call_command("move_nurseconnect_to_rthb", stdout=out)

        self.assertIn("Switching subscription for identity-uuid", out.getvalue())
        [subreq] = SubscriptionRequest.objects.all()
        self.assertEqual(subreq.messageset, 64)
        self.assertEqual(subreq.schedule, 164)

    @responses.activate
    def test_skips_existing_subscriptions(self):
        """
        If the current subscription is for the RTHB messageset and is in the
        correct place, no actions should be taken.
        """
        utils_tests.mock_get_messageset_by_shortname("nurseconnect_rthb.hw_full.1")
        utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_nurseconnect_rthb.hw_full.1"
        )
        utils_tests.mock_get_subscriptions(
            "?active=True&messageset_contains=nurseconnect",
            [
                {
                    "id": "subscription-uuid",
                    "identity": "identity-uuid",
                    "messageset": 63,
                    "next_sequence_number": 1,
                    "lang": "eng_ZA",
                    "active": True,
                }
            ],
        )

        out = StringIO()
        call_command("move_nurseconnect_to_rthb", stdout=out)

        self.assertEqual(out.getvalue(), "")
        self.assertEqual(SubscriptionRequest.objects.count(), 0)

    @responses.activate
    def test_skips_existing_subscriptions_whatsapp(self):
        """
        If the current subscription is for the RTHB messageset and is in the
        correct place, no actions should be taken.
        """
        utils_tests.mock_get_messageset_by_shortname("nurseconnect_rthb.hw_full.1")
        utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_nurseconnect_rthb.hw_full.1"
        )
        utils_tests.mock_get_subscriptions(
            "?active=True&messageset_contains=nurseconnect",
            [
                {
                    "id": "subscription-uuid",
                    "identity": "identity-uuid",
                    "messageset": 64,
                    "next_sequence_number": 1,
                    "lang": "eng_ZA",
                    "active": True,
                }
            ],
        )

        out = StringIO()
        call_command("move_nurseconnect_to_rthb", stdout=out)

        self.assertEqual(out.getvalue(), "")
        self.assertEqual(SubscriptionRequest.objects.count(), 0)
