import json

import responses
from django.test import TestCase, override_settings

from eventstore.tasks import mark_turn_contact_healthcheck_complete


class MarkTurnContactHealthCheckCompleteTests(TestCase):
    @override_settings(HC_TURN_URL=None, HC_TURN_TOKEN=None)
    @responses.activate
    def test_skips_when_no_settings(self):
        """
        Should not send anything if the settings aren't set
        """
        mark_turn_contact_healthcheck_complete("+27820001001")
        self.assertEqual(len(responses.calls), 0)

    @override_settings(HC_TURN_URL="https://turn", HC_TURN_TOKEN="token")
    @responses.activate
    def test_send_successful(self):
        """
        Should send with correct request data
        """
        responses.add(
            responses.PATCH, "https://turn/v1/contacts/27820001001/profile", json={}
        )
        mark_turn_contact_healthcheck_complete("+27820001001")
        [call] = responses.calls
        self.assertEqual(json.loads(call.request.body), {"healthcheck_completed": True})
        self.assertEqual(call.request.headers["Authorization"], "Bearer token")
        self.assertEqual(call.request.headers["Accept"], "application/vnd.v1+json")
