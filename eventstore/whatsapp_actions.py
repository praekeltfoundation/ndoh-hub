from celery import chain
from django.conf import settings

from changes.tasks import get_engage_inbound_and_reply
from eventstore.tasks import async_create_flow_start
from ndoh_hub.utils import normalise_msisdn


def handle_outbound(message):
    """
    Triggers all the actions that are required for this outbound message
    """
    if message.is_operator_message:
        handle_operator_message(message)


def handle_operator_message(message):
    """
    Triggers all the tasks that need to run for an outbound message from an operator
    """
    whatsapp_contact_id = message.data["_vnd"]["v1"]["chat"]["owner"]
    msisdn = normalise_msisdn(whatsapp_contact_id)
    return chain(
        get_engage_inbound_and_reply.s(),
        async_create_flow_start.s(
            flow=settings.RAPIDPRO_OPERATOR_REPLY_FLOW, urns=[f"tel:{msisdn}"]
        ),
    ).delay(whatsapp_contact_id, message.id)