from unittest import TestCase
from unittest.mock import Mock, patch

import responses
from django.test import override_settings

from eventstore.whatsapp_actions import (
    handle_inbound,
    handle_operator_message,
    handle_outbound,
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
            urns=["tel:+27820001001"],
        )


class HandleInboundTests(TestCase):
    def test_contact_update(self):
        """
        If the message is not over the fallback channel then it should update
        the preferred channel
        """
        message = Mock()

        with patch(
            "eventstore.whatsapp_actions.update_rapidpro_preferred_channel"
        ) as update:
            message.fallback_channel = True
            handle_inbound(message)
            update.assert_not_called()

            message.fallback_channel = False
            handle_inbound(message)
            update.assert_called_once_with(message)


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
