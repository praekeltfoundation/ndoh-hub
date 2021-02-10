import datetime
import json
from datetime import timedelta
from unittest.mock import Mock, patch

import responses
from django.conf import settings
from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.utils import timezone
from django_redis import get_redis_connection
from pytz import UTC
from temba_client.v2 import TembaClient

from eventstore import tasks
from eventstore.models import DeliveryFailure, Event
from eventstore.whatsapp_actions import (
    handle_edd_message,
    handle_event,
    handle_fallback_event,
    handle_inbound,
    handle_operator_message,
    handle_outbound,
    handle_whatsapp_delivery_error,
    handle_whatsapp_hsm_error,
    update_rapidpro_preferred_channel,
)
from registrations.models import JembiSubmission


class HandleOutboundTests(DjangoTestCase):
    def test_operator_message(self):
        """
        If the message is an operator message, then it should trigger the operator
        message action
        """
        message = Mock()

        with patch("eventstore.whatsapp_actions.handle_operator_message") as h:
            message.is_operator_message = False
            handle_outbound(message)
            h.assert_not_called()

            message.is_operator_message = True
            handle_outbound(message)
            h.assert_called_once_with(message)


class HandleOperatorMessageTests(DjangoTestCase):
    @override_settings(RAPIDPRO_OPERATOR_REPLY_FLOW="test-flow-uuid")
    @responses.activate
    def test_flow_triggered(self):
        """
        Triggers the correct rapidpro flow with the correct details
        """
        message = Mock()
        message.id = "test-id"
        message.data = {"_vnd": {"v1": {"chat": {"owner": "27820001001"}}}}
        tasks.rapidpro = TembaClient("textit.in", "test-token")
        responses.add(
            responses.GET,
            "http://engage/v1/contacts/27820001001/messages",
            json={
                "messages": [
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "author": {
                                    "id": "2ab15df1-082a-4420-8f1a-1fed53b13eba",
                                    "type": "OPERATOR",
                                },
                            }
                        },
                        "from": "27820001002",
                        "id": message.id,
                        "text": {"body": "Operator response"},
                        "timestamp": "1540803363",
                        "type": "text",
                    },
                    {
                        "_vnd": {"v1": {"direction": "inbound", "labels": []}},
                        "from": "27820001001",
                        "id": "ABGGJ3EVEUV_AhALwhRTSopsSmF7IxgeYIBz",
                        "text": {"body": "Inbound question"},
                        "timestamp": "1540802983",
                        "type": "text",
                    },
                ]
            },
        )
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-id",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"facility_code": "123456"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )
        responses.add(
            responses.POST,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={},
        )
        responses.add(responses.POST, "http://jembi/ws/rest/v1/helpdesk", json={})

        handle_operator_message(message)
        [jembi_request] = JembiSubmission.objects.all()
        jembi_request.request_data.pop("eid")
        self.assertEqual(
            jembi_request.request_data,
            {
                "class": "Unclassified",
                "cmsisdn": "+27820001001",
                "data": {"answer": "Operator response", "question": "Inbound question"},
                "dmsisdn": "+27820001001",
                "encdate": "20181029084943",
                "faccode": "123456",
                "mha": 1,
                "op": "56748517727534413379787391391214157498",
                "repdate": "20181029085603",
                "sid": "contact-id",
                "swt": 4,
                "type": 7,
            },
        )


class HandleInboundTests(DjangoTestCase):
    def test_contact_update(self):
        """
        If the message is not over the fallback channel then it should update
        the preferred channel
        """
        message = Mock()
        message.has_label.return_value = False

        with patch(
            "eventstore.whatsapp_actions.update_rapidpro_preferred_channel"
        ) as update:
            message.fallback_channel = True
            handle_inbound(message)
            update.assert_not_called()

            message.fallback_channel = False
            handle_inbound(message)
            update.assert_called_once_with(message)

    def test_handle_edd_label(self):
        """
        If the message has the EDD label then the correct flow should be started
        """
        message = Mock()
        message.has_label.return_value = False

        with patch("eventstore.whatsapp_actions.handle_edd_message") as handle:
            handle_inbound(message)
            handle.assert_not_called()

            message.has_label.return_value = True

            handle_inbound(message)
            handle.assert_called_once_with(message)


class UpdateRapidproPreferredChannelTests(DjangoTestCase):
    def test_contact_update_is_called(self):
        """
        Updates the rapidpro contact with the correct info
        """
        message = Mock()
        message.id = "test-id"
        message.fallback_channel = True
        message.contact_id = "27820001001"

        with patch("eventstore.tasks.rapidpro") as p:
            update_rapidpro_preferred_channel(message)

        p.update_contact.assert_called_once_with(
            "whatsapp:27820001001", fields={"preferred_channel": "WhatsApp"}
        )


class HandleEddLabelTests(DjangoTestCase):
    @override_settings(RAPIDPRO_EDD_LABEL_FLOW="test-flow-uuid")
    def test_handle_edd_message(self):
        """
        Triggers the correct flow with the correct details
        """
        message = Mock()
        message.data = {"_vnd": {"v1": {"chat": {"owner": "27820001001"}}}}

        with patch("eventstore.tasks.rapidpro") as p:
            handle_edd_message(message)

        p.create_flow_start.assert_called_once_with(
            extra={}, flow="test-flow-uuid", urns=["whatsapp:27820001001"]
        )


class HandleEventTests(DjangoTestCase):
    def test_expired_message(self):
        """
        If the event is an message expired error, then it should trigger the
        message delivery failed action
        """
        event = Mock()
        event.is_hsm_error = False
        event.is_whatsapp_failed_delivery_event = False

        with patch("eventstore.whatsapp_actions.handle_whatsapp_delivery_error") as h:
            event.is_message_expired_error = False
            handle_event(event)
            h.assert_not_called()

            event.is_message_expired_error = True
            handle_event(event)
            h.assert_called_once_with(event)

    def test_delivery_failed_error(self):
        """
        If the event is of type Failed, then it should trigger the message
        delivery failed action
        """
        event = Mock()
        event.is_message_expired_error = False
        event.is_hsm_error = False

        with patch("eventstore.whatsapp_actions.handle_whatsapp_delivery_error") as h:
            event.is_whatsapp_failed_delivery_event = False
            handle_event(event)
            h.assert_not_called()

            event.is_whatsapp_failed_delivery_event = True
            handle_event(event)
            h.assert_called_once_with(event)

    @override_settings(RAPIDPRO_OPTOUT_FLOW="test-flow-uuid")
    def test_fallback_channel_delivery_failure_error(self):
        """
        If the event is of type Failed, and uses the fallback channel,
        then it should trigger the message delivery failed action
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.FAILED
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        DeliveryFailure.objects.create(number_of_failures=4, contact_id="27820001001")

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_called_once_with(
            extra={
                "optout_reason": "sms_failure",
                "timestamp": event.timestamp.timestamp(),
                "babyloss_subscription": "FALSE",
                "delete_info_for_babyloss": "FALSE",
                "delete_info_consent": "FALSE",
                "source": "System",
            },
            flow="test-flow-uuid",
            urns=["whatsapp:27820001001"],
        )

    @override_settings(RAPIDPRO_OPTOUT_FLOW="test-flow-uuid")
    def test_fallback_channel_delivery_failure_duplicate(self):
        """
        If the event is of type Failed, and uses the fallback channel, but there
        was another failure in the last 24h then it should not trigger the
        message delivery failed action
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.FAILED
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now()

        DeliveryFailure.objects.create(number_of_failures=4, contact_id="27820001001")

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 4)

    @override_settings(RAPIDPRO_OPTOUT_FLOW="test-flow-uuid")
    def test_fallback_channel_delivery_failure_error_more_than_5(self):
        """
        If the event is of type Failed, and uses the fallback channel,
        then it should trigger the message delivery failed action
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.FAILED
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        DeliveryFailure.objects.create(number_of_failures=5, contact_id="27820001001")

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 6)

    def test_fallback_channel_delivery_failure_less_than_5(self):
        """
        If the event is of type Failed, and uses the fallback channel,
        but delivery failures are less than 5, should not call
        the rapidpro flow
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.FAILED
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 1)

    @override_settings(DISABLE_SMS_FAILURE_OPTOUTS=True)
    def test_fallback_channel_delivery_failure_optouts_disabled(self):
        """
        If the event is of type Failed, and uses the fallback channel,
        but SMS failure optouts are disabled, it should not call the rapidpro
        flow
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.FAILED
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        self.assertFalse(
            DeliveryFailure.objects.filter(contact_id="27820001001").exists()
        )

    def test_fallback_channel_successful_with_no_existing_delivery_failure(self):
        """
        If the event uses the fallback channel, but is a successful delivery
        with no existing delivery failure, it should not call the rapidpro flow
        and number_of_failures should be reset to 0
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.READ
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 0)

    def test_fallback_channel_successful_with_sent_status(self):
        """
        If the event uses the fallback channel, but with a send delivery status,
        it should not call the rapidpro flow, and number of failures should
        not be reset
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.SENT
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        DeliveryFailure.objects.create(number_of_failures=3, contact_id="27820001001")

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 3)

    def test_fallback_channel_successful_with_existing_delivery_failure(self):
        """
        If the event uses the fallback channel, but is a successful delivery
        with an existing delivery failure, it should not call the rapidpro flow
        and number_of_failures should be reset to 0
        """
        event = Event.objects.create()
        event.fallback_channel = True
        event.status = Event.READ
        event.recipient_id = "27820001001"
        event.timestamp = timezone.now() + timedelta(days=2)

        DeliveryFailure.objects.create(number_of_failures=1, contact_id="27820001001")

        with patch("eventstore.tasks.rapidpro") as p:
            handle_fallback_event(event)

        p.create_flow_start.assert_not_called()
        df = DeliveryFailure.objects.get(contact_id="27820001001")
        self.assertEqual(df.number_of_failures, 0)

    def test_hsm_error(self):
        """
        If the event is an HSM error, then it should trigger the HSM error
        action
        """
        event = Mock()
        event.is_message_expired_error = False
        event.is_whatsapp_failed_delivery_event = False

        with patch("eventstore.whatsapp_actions.handle_whatsapp_hsm_error") as h:
            event.is_hsm_error = False
            handle_event(event)
            h.assert_not_called()

            event.is_hsm_error = True
            handle_event(event)
            h.assert_called_once_with(event)


class HandleWhatsappEventsTests(DjangoTestCase):
    def setUp(self):
        redis = get_redis_connection("redis")
        key = f"hub_handle_whatsapp_delivery_error_27820001001"
        redis.delete(key)

        return super().setUp()

    @override_settings(RAPIDPRO_UNSENT_EVENT_FLOW="test-flow-uuid")
    @override_settings(ENABLE_UNSENT_EVENT_ACTION=True)
    def test_handle_whatsapp_hsm_error_successful(self):
        """
        Triggers the correct flow with the correct details
        """
        event = Mock()
        event.recipient_id = "27820001001"
        event.timestamp = datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)
        event.is_message_expired_error.return_value = False

        with patch("eventstore.tasks.rapidpro") as p:
            handle_whatsapp_hsm_error(event)

        p.create_flow_start.assert_called_once_with(
            extra={
                "popi_ussd": settings.POPI_USSD_CODE,
                "optout_ussd": settings.OPTOUT_USSD_CODE,
                "timestamp": 1_518_694_700,
            },
            flow="test-flow-uuid",
            urns=["whatsapp:27820001001"],
        )

    @override_settings(RAPIDPRO_UNSENT_EVENT_FLOW="test-flow-uuid")
    @override_settings(ENABLE_UNSENT_EVENT_ACTION=False)
    def test_handle_whatsapp_hsm_error_unsent_disabled(self):
        """
        Does nothing if ENABLE_UNSENT_EVENT_ACTION is False
        """
        event = Mock()
        event.recipient_id = "27820001001"
        event.data = {"errors": [{"title": "structure unavailable", "code": 123}]}
        event.is_message_expired_error.return_value = False

        with patch("eventstore.tasks.rapidpro") as p:
            handle_whatsapp_hsm_error(event)

        p.create_flow_start.assert_not_called()

    @responses.activate
    @patch("eventstore.tasks.get_utc_now")
    def test_handle_whatsapp_delivery_error(self, mock_get_utc_now):
        """
        Sends a SMS and updates the contact if the contact hasn't been sent this
        message in 30 days
        """
        timestamp = 1_543_999_390.069_308
        mock_get_utc_now.return_value = datetime.datetime.fromtimestamp(timestamp)

        event = Event.objects.create()
        event.recipient_id = "27820001001"
        event.fallback_channel = False

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-id",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        responses.add(responses.POST, "http://turn/v1/messages", json={})

        responses.add(
            responses.POST,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "uuid": "contact-id",
                "name": "",
                "language": "zul",
                "groups": [],
                "fields": {},
                "blocked": False,
                "stopped": False,
                "created_on": "2015-11-11T08:30:24.922024+00:00",
                "modified_on": "2015-11-11T08:30:25.525936+00:00",
                "urns": ["tel:+27820001001"],
            },
        )

        handle_whatsapp_delivery_error(event)

        [_, turn_call, rapidpro_post] = responses.calls

        self.assertEqual(
            json.loads(turn_call.request.body),
            {
                "preview_url": False,
                "recipient_type": "individual",
                "to": "27820001001",
                "type": "text",
                "text": {
                    "body": "Sibona ukuthi imiyalezo yeWhatsApp yakho yeMomConnect "
                    "ayifikanga. Ukuthola imiyalezo nge-SMS, phendula uthi "
                    "\u201cSMS\u201d (kusebenza izindleko ezijwayelekile)."
                },
            },
        )
        self.assertEqual(turn_call.request.headers["x-turn-fallback-channel"], "1")

        self.assertEqual(
            json.loads(rapidpro_post.request.body),
            {
                "fields": {
                    "whatsapp_undelivered_timestamp": "2018-12-05T08:43:10.069308"
                }
            },
        )

    @responses.activate
    @patch("eventstore.tasks.get_utc_now")
    def test_handle_whatsapp_delivery_error_with_old_timestamp(self, mock_get_utc_now):
        """
        Sends a SMS and updates the contact if the contact hasn't been sent this
        message in 30 days
        """
        timestamp = 1_543_999_390.069_308
        mock_get_utc_now.return_value = datetime.datetime.fromtimestamp(timestamp)

        event = Event.objects.create()
        event.recipient_id = "27820001001"
        event.fallback_channel = False

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-id",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {
                            "whatsapp_undelivered_timestamp": "2018-11-05 08:43:10"
                        },
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        responses.add(responses.POST, "http://turn/v1/messages", json={})

        responses.add(
            responses.POST,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "uuid": "contact-id",
                "name": "",
                "language": "zul",
                "groups": [],
                "fields": {},
                "blocked": False,
                "stopped": False,
                "created_on": "2015-11-11T08:30:24.922024+00:00",
                "modified_on": "2015-11-11T08:30:25.525936+00:00",
                "urns": ["tel:+27820001001"],
            },
        )

        handle_whatsapp_delivery_error(event)

        [_, turn_call, rapidpro_post] = responses.calls

        self.assertEqual(
            json.loads(turn_call.request.body),
            {
                "preview_url": False,
                "recipient_type": "individual",
                "to": "27820001001",
                "type": "text",
                "text": {
                    "body": "Sibona ukuthi imiyalezo yeWhatsApp yakho yeMomConnect "
                    "ayifikanga. Ukuthola imiyalezo nge-SMS, phendula uthi "
                    "\u201cSMS\u201d (kusebenza izindleko ezijwayelekile)."
                },
            },
        )
        self.assertEqual(turn_call.request.headers["x-turn-fallback-channel"], "1")

        self.assertEqual(
            json.loads(rapidpro_post.request.body),
            {
                "fields": {
                    "whatsapp_undelivered_timestamp": "2018-12-05T08:43:10.069308"
                }
            },
        )

    @responses.activate
    @patch("eventstore.tasks.get_utc_now")
    def test_handle_whatsapp_delivery_error_with_new_timestamp(self, mock_get_utc_now):
        """
        Doesn't send a SMS if contact recieved the message in the last 30 days
        """
        timestamp = 1_543_999_390.069_308
        mock_get_utc_now.return_value = datetime.datetime.fromtimestamp(timestamp)

        event = Event.objects.create()
        event.recipient_id = "27820001001"
        event.fallback_channel = False

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-id",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {
                            "whatsapp_undelivered_timestamp": "2018-11-06 08:43:10"
                        },
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        handle_whatsapp_delivery_error(event)

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @patch("eventstore.tasks.get_utc_now")
    def test_handle_whatsapp_delivery_error_with_empty_language(self, mock_get_utc_now):
        """
        Doesn't fail when the language is None
        """
        timestamp = 1_543_999_390.069_308
        mock_get_utc_now.return_value = datetime.datetime.fromtimestamp(timestamp)

        event = Event.objects.create()
        event.recipient_id = "27820001001"
        event.fallback_channel = False

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={
                "results": [
                    {
                        "uuid": "contact-id",
                        "name": "",
                        "language": None,
                        "groups": [],
                        "fields": {
                            "whatsapp_undelivered_timestamp": "2018-11-06 08:43:10"
                        },
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        handle_whatsapp_delivery_error(event)

        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    @patch("eventstore.tasks.get_utc_now")
    def test_handle_whatsapp_delivery_error_with_no_contact(self, mock_get_utc_now):
        """
        Doesn't fail when there is no contact
        """
        timestamp = 1_543_999_390.069_308
        mock_get_utc_now.return_value = datetime.datetime.fromtimestamp(timestamp)

        event = Event.objects.create()
        event.recipient_id = "27820001001"
        event.fallback_channel = False

        tasks.rapidpro = TembaClient("textit.in", "test-token")

        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?urn=whatsapp:27820001001",
            json={"results": [], "next": None},
        )

        handle_whatsapp_delivery_error(event)

        self.assertEqual(len(responses.calls), 1)
