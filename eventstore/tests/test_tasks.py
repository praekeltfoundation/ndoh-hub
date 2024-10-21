import datetime
import json
import uuid
from unittest import mock

import requests
import responses
from django.test import TestCase, override_settings
from django.utils import timezone
from temba_client.v2 import TembaClient

from eventstore import tasks
from eventstore.models import (
    ImportError,
    ImportRow,
    MomConnectImport,
    WhatsAppTemplateSendStatus,
)
from ndoh_hub import utils


def override_get_today():
    return datetime.datetime.strptime("20200117", "%Y%m%d").date()


class HandleOldWaitingForHelpdeskContactsTests(TestCase):
    def setUp(self):
        tasks.get_today = override_get_today
        tasks.rapidpro = TembaClient("textit.in", "test-token")

    def add_rapidpro_contact_list_response(
        self, contact_id, fields, urns=None
    ):
        if urns is None:
            urns = ["whatsapp:27820001001"]
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
        self, contact_id, fields, urns=None
    ):
        if urns is None:
            urns = ["whatsapp:27820001001"]
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
    @override_settings(
        HANDLE_EXPIRED_HELPDESK_CONTACTS_ENABLED=False,
    )
    def test_conversation_expired_disabled(self):
        tasks.handle_expired_helpdesk_contacts()

        self.assertEqual(len(responses.calls), 0)

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
            responses.POST, "http://turn/v1/chats/27820001001/archive", json={}
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
                "reason": "Auto archived after 11 days",
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


class ValidateMomConnectImportTests(TestCase):
    @mock.patch("eventstore.tasks.upload_momconnect_import")
    @responses.activate
    def test_success(self, upload_momconnect_import):
        """
        If the validation passes, then should be updated to validation complete
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp%3A27820001001",
            json={"results": [], "next": None},
        )

        mcimport = MomConnectImport.objects.create()
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.SAID,
        )
        tasks.validate_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.VALIDATED)

        upload_momconnect_import.delay.assert_called_once_with(mcimport.id)

    @responses.activate
    def test_fail_previously_opted_out(self):
        """
        If the mother has previously opted out, and hasn't chosen to opt in again,
        then validation should fail
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp%3A27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-uuid",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"opted_out": "TRUE"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27820001001"],
                    }
                ],
                "next": None,
            },
        )

        mcimport = MomConnectImport.objects.create()
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.SAID,
        )
        tasks.validate_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.ERROR)

        [error] = mcimport.errors.all()
        self.assertEqual(error.error_type, ImportError.ErrorType.OPTED_OUT_ERROR)

    @responses.activate
    def test_fail_already_registered(self):
        """
        If the mother is already receiving prebirth messages, then validation should
        fail
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp%3A27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-uuid",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"prebirth_messaging": "2"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27820001001"],
                    }
                ],
                "next": None,
            },
        )

        mcimport = MomConnectImport.objects.create()
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.SAID,
        )
        tasks.validate_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.ERROR)

        [error] = mcimport.errors.all()
        self.assertEqual(error.error_type, ImportError.ErrorType.ALREADY_REGISTERED)

    @responses.activate
    def test_fail_already_registered_postbirth(self):
        """
        If the mother is already receiving postbirth messages, then validation should
        fail
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp%3A27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-uuid",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"postbirth_messaging": "TRUE"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27820001001"],
                    }
                ],
                "next": None,
            },
        )

        mcimport = MomConnectImport.objects.create()
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.SAID,
        )
        tasks.validate_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.ERROR)

        [error] = mcimport.errors.all()
        self.assertEqual(error.error_type, ImportError.ErrorType.ALREADY_REGISTERED)


@override_settings(
    RAPIDPRO_PREBIRTH_CLINIC_FLOW="prebirth-clinic-flow-uuid",
    RAPIDPRO_POSTBIRTH_CLINIC_FLOW="postbirth-clinic-flow-uuid",
)
class UploadMomConnectImportTests(TestCase):
    def setUp(self):
        responses.add(
            responses.POST,
            "https://textit.in/api/v2/flow_starts.json",
            json={
                "uuid": "flow-start-uuid",
                "flow": {
                    "uuid": "prebirth-clinic-flow-uuid",
                    "name": "prebirth clinic",
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

    @responses.activate
    def test_success_sa_id(self):
        """
        If the validation passes, then should be updated to validation complete
        """

        mcimport = MomConnectImport.objects.create(
            status=MomConnectImport.Status.VALIDATED
        )
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.SAID,
            id_number="9001010001088",
        )
        tasks.upload_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.COMPLETE)

        request = json.loads(responses.calls[0].request.body)
        request["extra"].pop("timestamp")
        self.assertEqual(
            request,
            {
                "flow": "prebirth-clinic-flow-uuid",
                "urns": ["whatsapp:27820001001"],
                "extra": {
                    "clinic_code": "123456",
                    "edd": "2021-12-13",
                    "id_type": "sa_id",
                    "sa_id_number": "9001010001088",
                    "language": "eng",
                    "source": "MomConnect Import",
                    "swt": "7",
                    "registered_by": "+27820001001",
                    "passport_number": "",
                    "research_consent": "FALSE",
                },
            },
        )

    @responses.activate
    def test_success_passport(self):
        """
        If the validation passes, then should be updated to validation complete
        """

        mcimport = MomConnectImport.objects.create(
            status=MomConnectImport.Status.VALIDATED
        )
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.PASSPORT,
            passport_country=ImportRow.PassportCountry.ZW,
            passport_number="A123456",
        )
        tasks.upload_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.COMPLETE)

        request = json.loads(responses.calls[0].request.body)
        request["extra"].pop("timestamp")
        self.assertEqual(
            request,
            {
                "flow": "prebirth-clinic-flow-uuid",
                "urns": ["whatsapp:27820001001"],
                "extra": {
                    "clinic_code": "123456",
                    "edd": "2021-12-13",
                    "id_type": "passport",
                    "passport_number": "A123456",
                    "passport_origin": "zw",
                    "language": "eng",
                    "source": "MomConnect Import",
                    "swt": "7",
                    "sa_id_number": "",
                    "registered_by": "+27820001001",
                    "research_consent": "FALSE",
                },
            },
        )

    @responses.activate
    def test_success_dob(self):
        """
        If the validation passes, then should be updated to validation complete
        """

        mcimport = MomConnectImport.objects.create(
            status=MomConnectImport.Status.VALIDATED
        )
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            edd_year=2021,
            edd_month=12,
            edd_day=13,
            id_type=ImportRow.IDType.NONE,
            dob_year=1990,
            dob_month=2,
            dob_day=3,
        )
        tasks.upload_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.COMPLETE)

        request = json.loads(responses.calls[0].request.body)
        request["extra"].pop("timestamp")
        self.assertEqual(
            request,
            {
                "flow": "prebirth-clinic-flow-uuid",
                "urns": ["whatsapp:27820001001"],
                "extra": {
                    "clinic_code": "123456",
                    "edd": "2021-12-13",
                    "id_type": "dob",
                    "dob": "1990-02-03",
                    "language": "eng",
                    "source": "MomConnect Import",
                    "swt": "7",
                    "sa_id_number": "",
                    "passport_number": "",
                    "registered_by": "+27820001001",
                    "research_consent": "FALSE",
                },
            },
        )

    @responses.activate
    def test_success_postbirth(self):
        """
        If the validation passes, then should be updated to validation complete
        """

        mcimport = MomConnectImport.objects.create(
            status=MomConnectImport.Status.VALIDATED
        )
        mcimport.rows.create(
            row_number=2,
            msisdn="+27820001001",
            messaging_consent=True,
            facility_code="123456",
            baby_dob_year=2021,
            baby_dob_month=12,
            baby_dob_day=13,
            id_type=ImportRow.IDType.SAID,
            id_number="9001010001088",
        )
        tasks.upload_momconnect_import(mcimport.id)

        mcimport.refresh_from_db()
        self.assertEqual(mcimport.status, MomConnectImport.Status.COMPLETE)

        request = json.loads(responses.calls[0].request.body)
        request["extra"].pop("timestamp")
        self.assertEqual(
            request,
            {
                "flow": "postbirth-clinic-flow-uuid",
                "urns": ["whatsapp:27820001001"],
                "extra": {
                    "clinic_code": "123456",
                    "baby_dob": "2021-12-13",
                    "id_type": "sa_id",
                    "sa_id_number": "9001010001088",
                    "language": "eng",
                    "source": "MomConnect Import",
                    "swt": "7",
                    "registered_by": "+27820001001",
                    "passport_number": "",
                    "research_consent": "FALSE",
                },
            },
        )


class PostRandomContactsToSlackTests(TestCase):
    def setUp(self):
        tasks.rapidpro = TembaClient("textit.in", "test-token")

    @responses.activate
    @override_settings(
        TURN_URL="https://turn/",
        TURN_TOKEN="token",
        EXTERNAL_REGISTRATIONS_V2=True,
        SLACK_CHANNEL="test-slack",
        SLACK_URL="http://slack.com",
        RAPIDPRO_URL="rapidpro",
        RAPIDPRO_TOKEN="rapidpro-token",
        SLACK_TOKEN="slack-token",
    )
    def test_post_random_contacts_to_slack_channel(self):
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json",
            json={
                "results": [
                    {
                        "uuid": "148947f5-a3b6-4b6b-9e9b-25058b1b7800",
                        "name": "",
                        "language": "eng",
                        "groups": [],
                        "fields": {"helpdesk_timeout": None},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27712345682"],
                    },
                    {
                        "uuid": "128947f5-a3b6-4b3b-9e9b-25058b1b7801",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": "",
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2020-11-11T08:30:24.922024+00:00",
                        "modified_on": "2021-11-11T08:30:25.525936+00:00",
                        "urns": ["whatsapp:27720001010", "tel:0102584697"],
                    },
                ],
                "next": None,
            },
        )

        responses.add(
            responses.GET,
            "https://turn/v1/contacts/27712345682/messages",
            json={
                "chat": {
                    "permalink": "https://turn.io/c/8cc14-6a4e-4f2-82ed-c5",
                    "state_reason": "Re-opened by inbound message.",
                    "unread_count": 0,
                    "uuid": "68cc14b3-6a4e-4962-82ed-c572c6836fdd",
                }
            },
        )

        responses.add(
            responses.POST, "http://slack.com/api/chat.postMessage", json={"ok": True}
        )

        response = tasks.post_random_contacts_to_slack_channel()

        slack_message = responses.calls[-1]
        slack_body = requests.utils.unquote(slack_message.request.body)

        self.assertTrue(response["success"])
        self.assertEqual(len(response.get("results")), 10)
        self.assertEqual(slack_message.request.method, "POST")
        self.assertEqual(
            slack_message.request.url, "http://slack.com/api/chat.postMessage"
        )

        line1 = slack_body.split("\n")[1]
        self.assertEqual(
            line1.split("++++")[0],
            "1.+</contact/read/148947f5-a3b6-4b6b-9e9b-25058b1b7800/|RapidPro>",
        )
        self.assertEqual(
            line1.split("++++")[1], "<https://turn.io/c/8cc14-6a4e-4f2-82ed-c5|Turn>"
        )

    @responses.activate
    @override_settings(TURN_URL="https://turn/", TURN_TOKEN="token")
    def test_get_random_contact(self):
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json",
            json={"next": None, "previous": None, "results": []},
        )

        responses.add(
            responses.GET,
            "http://turn/v1/contacts/27781234567/messages",
            json={
                "chat": {
                    "owner": "+27836378500",
                    "permalink": "https://app.turn.io/c/68cc14-462-8ed-c5df",
                    "uuid": "68cc14b3-6a4e-4962-82ed-c572c6836fdd",
                }
            },
        )

        data, response = tasks.get_random_contact()

        contacts = responses.calls[-1]

        self.assertEqual(contacts.request.body, None)
        self.assertEqual(response, None)


class GetTurnContactProfileTests(TestCase):
    def setUp(self):
        tasks.rapidpro = TembaClient("textit.in", "test-token")

    @responses.activate
    @override_settings(TURN_URL="http://turn/", TURN_TOKEN="token")
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
        response = tasks.get_turn_profile_link("27781234567")

        self.assertEqual(type(response), str)
        self.assertEqual(
            str(response), "https://app.turn.io/c/68cc14-6a4e-4962-82ed-c576fdd"
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
        response = tasks.get_turn_profile_link(contact)

        self.assertEqual(response, None)


class SendSlackMessageTests(TestCase):
    def setUp(self):
        self.contact_details = [
            {1: "http://con.co.za/contact/dcc-42-a1-a3/ http://turn.io/c/6b3-6ad-c6c"},
            {2: "http://con.co.za/contact/b29-4e-ac-fd/ http://turn.io/c/ea-3b1-74d"},
            {3: "http://con.co.za/contact/30b-230c/ http://turn.io/c/cd-0b-4ce2-a97"},
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
                "updated": 1_639_475_940,
                "team_id": "T0CJ9CT7W",
            },
        )

        response = utils.send_slack_message("test-mom", str(self.contact_details))

        self.assertEqual(response, True)


class UpdateWhatsappTemplateSendStatus(TestCase):
    def setUp(self):
        self.status = WhatsAppTemplateSendStatus.objects.create(
            message_id="test-message-id"
        )

    @mock.patch("eventstore.tasks.async_create_flow_start")
    def test_update_status_whatsapp(self, mock_flow_start):
        """
        If the event is received the status record needs to be updated
        """
        tasks.update_whatsapp_template_send_status(self.status.message_id)

        self.status.refresh_from_db()

        self.assertEqual(
            self.status.status, WhatsAppTemplateSendStatus.Status.EVENT_RECEIVED
        )
        self.assertEqual(self.status.preferred_channel, "WhatsApp")
        self.assertIsNotNone(self.status.event_received_at)

        mock_flow_start.assert_not_called()

    @mock.patch("eventstore.tasks.async_create_flow_start")
    def test_update_status_whatsapp_ready(self, mock_flow_start):
        """
        If the event is received and it has a flow to start, the status record needs to
        be updated and the async_create_flow_start task needs to be called
        """
        self.status.flow_uuid = uuid.uuid4()
        self.status.save()
        tasks.update_whatsapp_template_send_status(self.status.message_id)

        self.status.refresh_from_db()

        self.assertEqual(
            self.status.status, WhatsAppTemplateSendStatus.Status.ACTION_COMPLETED
        )
        self.assertEqual(self.status.preferred_channel, "WhatsApp")
        self.assertIsNotNone(self.status.event_received_at)
        self.assertIsNotNone(self.status.action_completed_at)

        mock_flow_start.assert_called()

    @mock.patch("eventstore.tasks.async_create_flow_start")
    def test_update_status_sms(self, mock_flow_start):
        """
        If the event is received with SMS as the preferred_channel the status record
        needs to be updated
        """
        tasks.update_whatsapp_template_send_status(self.status.message_id, "SMS")

        self.status.refresh_from_db()

        self.assertEqual(
            self.status.status, WhatsAppTemplateSendStatus.Status.EVENT_RECEIVED
        )
        self.assertEqual(self.status.preferred_channel, "SMS")
        self.assertIsNotNone(self.status.event_received_at)
        mock_flow_start.assert_not_called()

    @mock.patch("eventstore.tasks.async_create_flow_start")
    def test_update_status_action_completed(self, mock_flow_start):
        """
        If the status record is already action_completed then do nothing.
        """
        self.status.status = WhatsAppTemplateSendStatus.Status.ACTION_COMPLETED
        self.status.save()
        tasks.update_whatsapp_template_send_status(self.status.message_id, "SMS")

        self.status.refresh_from_db()

        self.assertEqual(
            self.status.status, WhatsAppTemplateSendStatus.Status.ACTION_COMPLETED
        )
        self.assertEqual(self.status.preferred_channel, "WhatsApp")
        self.assertIsNone(self.status.event_received_at)
        mock_flow_start.assert_not_called()


class ProcessWhatsAppTemplateSendStatusTests(TestCase):
    def setUp(self):
        self.contact_uuid = "06639860-1967-4b2b-97a5-f17b094f3763"
        self.flow_uuid = "f4cc0bfb-57ec-4fd9-8c32-4a6a72b14d53"
        self.status_ignored = WhatsAppTemplateSendStatus.objects.create(
            message_id="test-message-id1"
        )
        self.status_ready = WhatsAppTemplateSendStatus.objects.create(
            message_id="test-message-id2",
            status=WhatsAppTemplateSendStatus.Status.EVENT_RECEIVED,
            data={"status": "ready"},
            flow_uuid=self.flow_uuid,
            contact_uuid=self.contact_uuid,
        )
        self.status_expired = WhatsAppTemplateSendStatus.objects.create(
            message_id="test-message-id3",
            status=WhatsAppTemplateSendStatus.Status.WIRED,
            data={"status": "expired"},
            flow_uuid=self.flow_uuid,
            contact_uuid=self.contact_uuid,
        )
        self.status_expired.sent_at = timezone.now() - datetime.timedelta(hours=4)
        self.status_expired.save()

    @mock.patch("eventstore.tasks.async_create_flow_start")
    def test_starts_flows(self, mock_async_flow_start):
        tasks.process_whatsapp_template_send_status()

        self.assertEqual(
            mock_async_flow_start.delay.mock_calls,
            [
                mock.call(
                    extra={"status": "ready", "preferred_channel": "WhatsApp"},
                    flow=self.status_ready.flow_uuid,
                    contacts=[self.status_ready.contact_uuid],
                ),
                mock.call(
                    extra={"status": "expired", "preferred_channel": "WhatsApp"},
                    flow=self.status_expired.flow_uuid,
                    contacts=[self.status_expired.contact_uuid],
                ),
            ],
        )

        self.status_ready.refresh_from_db()
        self.status_expired.refresh_from_db()

        self.assertEqual(
            self.status_ready.status, WhatsAppTemplateSendStatus.Status.ACTION_COMPLETED
        )
        self.assertEqual(
            self.status_expired.status,
            WhatsAppTemplateSendStatus.Status.ACTION_COMPLETED,
        )
