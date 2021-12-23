from django.test import TestCase, override_settings
from temba_client.v2 import TembaClient

from eventstore import random_contacts
import responses


class HandleRapidProContactsTests(TestCase):
    def setUp(self):
        random_contacts.rapidpro = TembaClient("textit.in", "test-token")

    @responses.activate
    @override_settings(
        RAPIDPRO_URL="https://rapidpro",
        RAPIDPRO_TOKEN="rapidpro_token",
        EXTERNAL_REGISTRATIONS_V2=True,
    )
    def test_get_contacts(self):
        responses.add(
            responses.GET,
            "https://rapidpro/api/v2/contacts.json",
            json=[
                {
                    "uuid": "148947f5-a3b6-4b6b-9e9b-25058b1b7800",
                    "urns": ["whatsapp:27786159018"],
                },
                {
                    "uuid": "128947f5-a3b6-4b3b-9e9b-25058b1b7801",
                    "urns": ["whatsapp:27720001010", "tel:0102584697"],
                },
            ],
        )

        response = random_contacts.get_contacts()

        self.assertEqual(type(response), dict)
        self.assertEqual(type(response.get("results")), list)
        self.assertIn("success", response)


class HandleTurnProfileTests(TestCase):
    def setUp(self):
        random_contacts.rapidpro = TembaClient("textit.in", "test-token")

    @responses.activate
    @override_settings(TURN_URL="http://turn", TURN_TOKEN="token")
    def test_get_turn_profile_link(self):
        responses.add(
            responses.GET,
            "http://turn/v1/contacts/27781234567/messages",
            json={
                "chat": {
                    "assigned_to": None,
                    "owner": "+27836378500",
                    "permalink": "https://app.turn.io/c/68cc14-6a4e-4962-82ed-c576fdd",
                    "state": "OPEN",
                    "state_reason": "Re-opened by inbound message.",
                    "unread_count": 0,
                    "uuid": "68cc14b3-6a4e-4962-82ed-c572c6836fdd",
                }
            },
            status=200,
        )
        response = random_contacts.get_turn_profile_link("27781234567")

        self.assertEqual(type(response), str)
        self.assertEqual(
            str(response), "https://app.turn.io/c/68cc14b3-6a4e-4962-82ed-c572c6836fdd"
        )
        self.assertNotEqual(
            type(response), "https://app.turn.io/c/68cc14b3-6a4e-4962-82ed-c572c6836fdz"
        )

    @responses.activate
    def test_get_turn_profile_link_none_contact(self):
        contact = None
        responses.add(
            responses.GET,
            "http://turn/v1/contacts//messages",
            json={
                "chat": {
                    "assigned_to": None,
                    "owner": "+27836378500",
                    "permalink": "https://app.turn.io/c/68cc13-6a4e-4962-82ed-c572cfdc",
                    "state": "OPEN",
                    "state_reason": "Re-opened by inbound message.",
                    "unread_count": 0,
                    "uuid": "68cc14b3-6a4e-4962-82ed-c572c6836fdc",
                }
            },
            status=200,
        )
        response = random_contacts.get_turn_profile_link(contact)

        self.assertEqual(response, None)


class HandleSendSlackMessage(TestCase):
    def setUp(self):
        self.contact_details = [
            {
                "Rapid_Pro_Link: ": "http://connect.co.za/contact/read/dc-7c-42-a1-a3/",
                "Turn_Profile_Link": "http://app.turn.io/c/684b3-6ae-496-82d-c6c",
            },
            {
                "Rapid_Pro_Link: ": "http://connect.co.za/contact/read/b2-59-4e-ac-fd/",
                "Turn_Profile_Link": "http://app.turn.io/c/0e11a-13a2-4284-b961-3474d",
            },
            {
                "Pro_Link: ": "http://connect.co.za/contact/read/341-2d1-49b-b0b-230c/",
                "Profile_Link": "http://app.turn.io/c/cda524fb-80b9-40c0-a3e2-a452b797",
            },
        ]

    @responses.activate
    @override_settings(SLACK_URL="http://slack.com", SLACK_TOKEN="slack_token")
    def test_send_slack_message(self):
        responses.add(
            responses.POST,
            "http://slack.com/api/chat.postMessage",
            json={
                "ok": True,
                "token": "slack_token",
                "channel": "test-mon",
                "text": self.contact_details,
                "deleted": False,
                "updated": 1639475940,
                "team_id": "T0CJ9CT7W",
            },
        )

        response = random_contacts.send_slack_message(self.contact_details)

        self.assertEqual(response, True)
