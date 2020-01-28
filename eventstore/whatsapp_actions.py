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
        urn=f"whatsapp:{message.contact_id}", fields={"preferred_channel": "WhatsApp"}
    )


def handle_event(event):
    """
    Triggers all the actions that are required for this event
    """
    if not event.fallback_channel:
        handle_whatsapp_event(event)


def handle_whatsapp_event(event):
    # 410: Message expired
    if any(error["code"] == 410 for error in event.data["errors"]):
        # TODO: handle whatsapp timeout system event
        pass
    elif settings.ENABLE_UNSENT_EVENT_ACTION:
        hsm_error = False
        for error in event.data["errors"]:
            if "structure unavailable" in error["title"]:
                hsm_error = True
            if "envelope mismatch" in error["title"]:
                hsm_error = True

        if hsm_error:
            async_create_flow_start.delay(
                extra={},
                flow=settings.RAPIDPRO_UNSENT_EVENT_FLOW,
                urns=[f"whatsapp:{event.recipient_id}"],
            )
