import datetime
from unittest import TestCase
from unittest.mock import Mock, patch

import responses
from django.conf import settings
from django.test import override_settings
from pytz import UTC

from eventstore.whatsapp_actions import (
    handle_edd_message,
    handle_event,
    handle_inbound,
    handle_operator_message,
    handle_outbound,
    handle_whatsapp_hsm_error,
    update_rapidpro_preferred_channel,
)


class HandleOutboundTests(TestCase):
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


class HandleOperatorMessageTests(TestCase):
    @override_settings(RAPIDPRO_OPERATOR_REPLY_FLOW="test-flow-uuid")
    @responses.activate
    def test_flow_triggered(self):
        """
        Triggers the correct rapidpro flow with the correct details
        """
        message = Mock()
        message.id = "test-id"
        message.data = {"_vnd": {"v1": {"chat": {"owner": "27820001001"}}}}
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

        with patch("eventstore.tasks.rapidpro") as p:
            handle_operator_message(message)
        p.create_flow_start.assert_called_once_with(
            extra={
                "inbound_text": "Inbound question",
                "inbound_timestamp": 1540802983,
                "inbound_address": "27820001001",
                "inbound_labels": [],
                "reply_text": "Operator response",
                "reply_timestamp": 1540803363,
                "reply_operator": 56748517727534413379787391391214157498,
            },
            flow="test-flow-uuid",
            urns=["whatsapp:27820001001"],
        )


class HandleInboundTests(TestCase):
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


class UpdateRapidproPreferredChannelTests(TestCase):
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


class HandleEddLabelTests(TestCase):
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


class HandleEventTests(TestCase):
    def test_expired_message(self):
        """
        If the event is an message expired error, then it should trigger the
        message expired action
        """
        event = Mock()
        event.is_hsm_error = False

        with patch(
            "eventstore.whatsapp_actions.handle_whatsapp_message_expired_error"
        ) as h:
            event.is_message_expired_error = False
            handle_event(event)
            h.assert_not_called()

            event.is_message_expired_error = True
            handle_event(event)
            h.assert_called_once_with(event)

    def test_hsm_error(self):
        """
        If the event is an HSM error, then it should trigger the HSM error
        action
        """
        event = Mock()
        event.is_message_expired_error = False

        with patch("eventstore.whatsapp_actions.handle_whatsapp_hsm_error") as h:
            event.is_hsm_error = False
            handle_event(event)
            h.assert_not_called()

            event.is_hsm_error = True
            handle_event(event)
            h.assert_called_once_with(event)


class HandleWhatsappEventsTests(TestCase):
    @override_settings(RAPIDPRO_UNSENT_EVENT_FLOW="test-flow-uuid")
    @override_settings(ENABLE_UNSENT_EVENT_ACTION=True)
    def test_handle_whatsapp_hsm_error_successful(self):
        """
        Triggers the correct flow with the correct details
        """
        event = Mock()
        event.recipient_id = "27820001001"
        event.timestamp = datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)

        with patch("eventstore.tasks.rapidpro") as p:
            handle_whatsapp_hsm_error(event)

        p.create_flow_start.assert_called_once_with(
            extra={
                "popi_ussd": settings.POPI_USSD_CODE,
                "optout_ussd": settings.OPTOUT_USSD_CODE,
                "timestamp": 1518694700,
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

        with patch("eventstore.tasks.rapidpro") as p:
            handle_whatsapp_hsm_error(event)

        p.create_flow_start.assert_not_called()
