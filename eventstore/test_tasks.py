import datetime
import json
from unittest import mock

import responses
from django.test import TestCase, override_settings
from temba_client.v2 import TembaClient

from eventstore import tasks
from eventstore.models import Covid19Triage, ImportError, ImportRow, MomConnectImport
from registrations.models import ClinicCode


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


@override_settings(RAPIDPRO_PREBIRTH_CLINIC_FLOW="prebirth-clinic-flow-uuid")
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


class ProcessAdaAssessmentNotificationTests(TestCase):
    def setUp(self):
        tasks.get_today = override_get_today
        tasks.rapidpro = TembaClient("textit.in", "test-token")

    @responses.activate
    def test_no_contact(self):
        """
        If there's no rapidpro contact with the specified ID, then ignore notification
        """
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=does-not-exist",
            json={"results": [], "next": None},
        )
        tasks.process_ada_assessment_notification(
            username="test",
            id="abc123",
            patient_id="does-not-exist",
            patient_dob="1990-01-02",
            observations={},
            timestamp="2021-01-02T03:04:05Z",
        )
        self.assertEqual(Covid19Triage.objects.count(), 0)

    @responses.activate
    def test_no_facility(self):
        """
        If there's no facility for the contact's facility code, then ignore notification
        """
        rpcontact = {
            "uuid": "contact-uuid",
            "name": "",
            "language": "zul",
            "groups": [],
            "fields": {"clinic_code": "123456"},
            "blocked": False,
            "stopped": False,
            "created_on": "2015-11-11T08:30:24.922024+00:00",
            "modified_on": "2015-11-11T08:30:25.525936+00:00",
            "urns": ["whatsapp:27820001001"],
        }
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=does-not-exist",
            json={"results": [rpcontact], "next": None},
        )
        tasks.process_ada_assessment_notification(
            username="test",
            id="abc123",
            patient_id="does-not-exist",
            patient_dob="1990-01-02",
            observations={},
            timestamp="2021-01-02T03:04:05Z",
        )
        self.assertEqual(Covid19Triage.objects.count(), 0)

    @responses.activate
    def test_valid(self):
        """
        Creates a Covid19Triage with the information
        """
        ClinicCode.objects.create(
            code="123456",
            value="123456",
            uid="abc123",
            name="Test clinic",
            province="ZA-WC",
            location="-12.34+043.21/",
        )
        rpcontact = {
            "uuid": "contact-uuid",
            "name": "",
            "language": "zul",
            "groups": [],
            "fields": {"facility_code": "123456"},
            "blocked": False,
            "stopped": False,
            "created_on": "2015-11-11T08:30:24.922024+00:00",
            "modified_on": "2015-11-11T08:30:25.525936+00:00",
            "urns": ["whatsapp:27820001001"],
        }
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=contact-uuid",
            json={"results": [rpcontact], "next": None},
        )
        responses.add(
            responses.POST,
            "https://textit.in/api/v2/contacts.json?uuid=contact-uuid",
            json=rpcontact,
        )
        tasks.process_ada_assessment_notification(
            username="test",
            id="abc123",
            patient_id="contact-uuid",
            patient_dob="1990-01-02",
            observations={
                "fever": False,
                "cough": False,
                "sore throat": False,
                "diminished sense of taste": False,
                "reduced sense of smell": True,
                "possible contact with 2019 novel coronavirus": False,
            },
            timestamp="2021-01-02T03:04:05Z",
        )
        [triage] = Covid19Triage.objects.all()
        self.assertEqual(triage.deduplication_id, "abc123")
        self.assertEqual(triage.msisdn, "+27820001001")
        self.assertEqual(triage.source, "Ada")
        self.assertEqual(triage.age, Covid19Triage.AGE_18T40),
        self.assertEqual(triage.date_of_birth, datetime.date(1990, 1, 2)),
        self.assertEqual(triage.province, "ZA-WC"),
        self.assertEqual(triage.city, "Test clinic"),
        self.assertEqual(triage.city_location, "-12.34+043.21/"),
        self.assertEqual(triage.fever, False),
        self.assertEqual(triage.cough, False),
        self.assertEqual(triage.sore_throat, False),
        self.assertEqual(triage.smell, True),
        self.assertEqual(triage.exposure, Covid19Triage.EXPOSURE_NO),
        self.assertEqual(triage.tracing, False),
        self.assertEqual(triage.risk, Covid19Triage.RISK_MODERATE),
        self.assertEqual(triage.gender, Covid19Triage.GENDER_FEMALE),
        self.assertEqual(
            triage.completed_timestamp,
            datetime.datetime(2021, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(triage.created_by, "test"),
        self.assertEqual(triage.data, {"age": 30, "pregnant": False}),
