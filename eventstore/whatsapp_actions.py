from celery import chain
from django.conf import settings

from changes.tasks import get_engage_inbound_and_reply
from eventstore.tasks import async_create_flow_start, update_rapidpro_contact
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


def handle_inbound(message):
    """
    Triggers all the actions that are required for this inbound message
    """
    if not message.fallback_channel:
        update_rapidpro_preferred_channel(message)


def update_rapidpro_preferred_channel(message):
    update_rapidpro_contact.delay(
        urn=f"whatsapp:{message.contact_id}", fields={"preferred_channnel": "WhatsApp"}
    )
