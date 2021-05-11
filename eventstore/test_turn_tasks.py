import json

import responses
from django.test import TestCase, override_settings

from eventstore.turn_tasks import update_turn_contact


class UpdateTurnContactTaskTest(TestCase):
    @responses.activate
    @override_settings(HC_TURN_URL="https://turn", HC_TURN_TOKEN="token")
    def test_update_turn_contact_task(self):
        responses.add(
            responses.PATCH,
            f"https://turn/v1/contacts/27820001001/profile",
            json={"test_field": "test_value"},
            status=201,
        )

        update_turn_contact("+27820001001", "test_field", "test_value")

        [patch] = responses.calls

        self.assertEqual(
            patch.request.url, f"https://turn/v1/contacts/27820001001/profile"
        )
        self.assertEqual(json.loads(patch.request.body), {"test_field": "test_value"})
