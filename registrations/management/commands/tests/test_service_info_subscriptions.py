from django.core.management import call_command
from django.test import TestCase
import responses

from ndoh_hub import utils_tests
from registrations.management.commands.service_info_subscriptions import (
    Command)
from registrations.models import SubscriptionRequest


class ServiceInfoSubscriptionsTests(TestCase):
    @responses.activate
    def test_identity_has_service_info_subscription_true(self):
        """
        If the identity has an active service info subscription, should return
        True
        """
        utils_tests.mock_get_subscriptions(
            "?active=True&identity=identity-uuid", [
                {"messageset": 1}, {"messageset": 2}])
        cmd = Command()
        res = cmd.identity_has_service_info_subscription({
            1: "whatsapp_momconnect_prebirth.hw_full.1",
            2: "whatsapp_service_info.hw_full.1",
            3: "whatsapp_popi.hw_full.1",
        }, "identity-uuid")
        self.assertTrue(res)

    @responses.activate
    def test_identity_has_service_info_subscription_false(self):
        """
        If the identity does not have an active service info subscription,
        should return False
        """
        utils_tests.mock_get_subscriptions(
            "?active=True&identity=identity-uuid", [
                {"messageset": 1}, {"messageset": 3}])
        cmd = Command()
        res = cmd.identity_has_service_info_subscription({
            1: "whatsapp_momconnect_prebirth.hw_full.1",
            2: "whatsapp_service_info.hw_full.1",
            3: "whatsapp_popi.hw_full.1",
        }, "identity-uuid")
        self.assertFalse(res)

    @responses.activate
    def test_service_info_subscriptions(self):
        """
        For each identity that has an active subscription, should create a
        service info subscription request if they don't already have one.
        """
        utils_tests.mock_get_messagesets([
            {"id": 1, "short_name": "whatsapp_momconnect_prebirth.hw_full.1"},
            {"id": 2, "short_name": "whatsapp_service_info.hw_full.1"},
            {"id": 3, "short_name": "whatsapp_momconnect_prebirth.patient.1"},
        ])
        utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_service_info.hw_full.1")
        utils_tests.mock_get_subscriptions(
            "?active=True&messageset_contains=whatsapp_momconnect_", [
                # already has service info subscription
                {
                    "identity": "identity-uuid1",
                    "lang": "zul_ZA",
                    "messageset": 1,
                    "sequence_number": 5,
                    "next_sequence_number": 3,
                },
                # should get service subscription added
                {
                    "identity": "identity-uuid2",
                    "lang": "sso_ZA",
                    "messageset": 1,
                    "sequence_number": 7,
                    "next_sequence_number": 5,
                },
                # subscription is not for full messageset
                {
                    "identity": "identity-uuid2",
                    "lang": "sso_ZA",
                    "messageset": 3,
                    "sequence_number": 7,
                    "next_sequence_number": 5,
                },
            ]
        )
        utils_tests.mock_get_subscriptions(
            "?active=True&identity=identity-uuid1", [
                {"messageset": 1}, {"messageset": 2}])
        utils_tests.mock_get_subscriptions(
            "?active=True&identity=identity-uuid2", [
                {"messageset": 1}, {"messageset": 3}])

        call_command(
            "service_info_subscriptions",
            "--sbm-url", "http://sbm/",
            "--sbm-token", "sbmtoken"
        )

        [subreq] = SubscriptionRequest.objects.all()
        self.assertEqual(subreq.messageset, 95)
        self.assertEqual(subreq.identity, "identity-uuid2")
        self.assertEqual(subreq.next_sequence_number, 1)
        self.assertEqual(subreq.lang, "sso_ZA")
        self.assertEqual(subreq.schedule, 123)
