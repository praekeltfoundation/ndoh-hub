import datetime
import json

import responses
from django.test import TestCase, override_settings
from temba_client.v2 import TembaClient

from eventstore import tasks


def override_get_today():
    return datetime.datetime.strptime("20200117", "%Y%m%d").date()


class MarkTurnContactHealthCheckCompleteTests(TestCase):
    @override_settings(HC_TURN_URL=None, HC_TURN_TOKEN=None)
    @responses.activate
    def test_skips_when_no_settings(self):
        """
        Should not send anything if the settings aren't set
        """
        tasks.mark_turn_contact_healthcheck_complete("+27820001001")
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
        tasks.mark_turn_contact_healthcheck_complete("+27820001001")
        [call] = responses.calls
        self.assertEqual(json.loads(call.request.body), {"healthcheck_completed": True})
        self.assertEqual(call.request.headers["Authorization"], "Bearer token")
        self.assertEqual(call.request.headers["Accept"], "application/vnd.v1+json")


class HandleOldWaitingForHelpdeskContactsTests(TestCase):
    def setUp(self):
        tasks.get_today = override_get_today
        tasks.rapidpro = TembaClient("textit.in", "test-token")

    def add_rapidpro_contact_list_response(
        self, contact_id, fields, urns=["whatsapp:27820001001"]
    ):
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?group=Waiting+for+helpdesk",
            json={
                "results": [
                    {
                        "uuid": contact_id,
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": fields,
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": urns,
                    }
                ],
                "next": None,
            },
        )

    def add_rapidpro_contact_update_response(
        self, contact_id, fields, urns=["whatsapp:27820001001"]
    ):
        responses.add(
            responses.POST,
            f"https://textit.in/api/v2/contacts.json?uuid={contact_id}",
            json={
                "uuid": contact_id,
                "name": "",
                "language": "zul",
                "groups": [],
                "fields": fields,
                "blocked": False,
                "stopped": False,
                "created_on": "2015-11-11T08:30:24.922024+00:00",
                "modified_on": "2015-11-11T08:30:25.525936+00:00",
                "urns": urns,
            },
        )

    @responses.activate
    def test_conversation_expired(self):

        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        self.add_rapidpro_contact_list_response(
            contact_id,
            {
                "helpdesk_timeout": "2020-01-06",
                "wait_for_helpdesk": "TRUE",
                "helpdesk_message_id": "ABGGJ4NjeFMfAgo-sCqKaSQU4UzP",
            },
        )

        self.add_rapidpro_contact_update_response(
            contact_id,
            {
                "helpdesk_timeout": None,
                "wait_for_helpdesk": None,
                "helpdesk_message_id": None,
            },
        )

        responses.add(
            responses.POST, f"http://turn/v1/chats/27820001001/archive", json={}
        )

        tasks.handle_expired_helpdesk_contacts()

        [_, rapidpro_update, turn_archive] = responses.calls
        self.assertEqual(
            json.loads(rapidpro_update.request.body),
            {
                "fields": {
                    "helpdesk_timeout": None,
                    "wait_for_helpdesk": None,
                    "helpdesk_message_id": None,
                }
            },
        )
        self.assertEqual(
            json.loads(turn_archive.request.body),
            {
                "before": "ABGGJ4NjeFMfAgo-sCqKaSQU4UzP",
                "reason": f"Auto archived after 11 days",
            },
        )

    @responses.activate
    def test_conversation_not_expired(self):
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        self.add_rapidpro_contact_list_response(
            contact_id,
            {
                "helpdesk_timeout": "2020-01-09",
                "wait_for_helpdesk": "TRUE",
                "helpdesk_message_id": "ABGGJ4NjeFMfAgo-sCqKaSQU4UzP",
            },
        )

        tasks.handle_expired_helpdesk_contacts()

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_conversation_fields_not_populated(self):
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        self.add_rapidpro_contact_list_response(
            contact_id, {"wait_for_helpdesk": "TRUE", "helpdesk_message_id": None}
        )

        tasks.handle_expired_helpdesk_contacts()

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_conversation_expired_no_urn(self):
        contact_id = "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"

        self.add_rapidpro_contact_list_response(
            contact_id,
            {
                "helpdesk_timeout": "2020-01-06",
                "wait_for_helpdesk": "TRUE",
                "helpdesk_message_id": "ABGGJ4NjeFMfAgo-sCqKaSQU4UzP",
            },
            [],
        )

        self.add_rapidpro_contact_update_response(
            contact_id,
            {
                "helpdesk_timeout": None,
                "wait_for_helpdesk": None,
                "helpdesk_message_id": None,
            },
            [],
        )

        tasks.handle_expired_helpdesk_contacts()

        [_, rapidpro_update] = responses.calls
        self.assertEqual(
            json.loads(rapidpro_update.request.body),
            {
                "fields": {
                    "helpdesk_timeout": None,
                    "wait_for_helpdesk": None,
                    "helpdesk_message_id": None,
                }
            },
        )
