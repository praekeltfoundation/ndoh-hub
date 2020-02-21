from celery import chain
from django.conf import settings

from changes.tasks import get_engage_inbound_and_reply
from eventstore.models import DeliveryFailures, Event
from eventstore.tasks import (
    async_create_flow_start,
    async_handle_whatsapp_delivery_error,
    update_rapidpro_contact,
)
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
    # This should be in "+27xxxxxxxxx" format, but just in case it isn't
    msisdn = normalise_msisdn(whatsapp_contact_id)
    return chain(
        get_engage_inbound_and_reply.s(),
        async_create_flow_start.s(
            flow=settings.RAPIDPRO_OPERATOR_REPLY_FLOW,
            urns=[f"whatsapp:{msisdn.lstrip('+')}"],
        ),
    ).delay(whatsapp_contact_id, message.id)


def handle_inbound(message):
    """
    Triggers all the actions that are required for this inbound message
    """
    if not message.fallback_channel:
        update_rapidpro_preferred_channel(message)

    if message.has_label("EDD"):
        handle_edd_message(message)


def update_rapidpro_preferred_channel(message):
    update_rapidpro_contact.delay(
        urn=f"whatsapp:{message.contact_id}", fields={"preferred_channel": "WhatsApp"}
    )


def handle_edd_message(message):
    whatsapp_contact_id = message.data["_vnd"]["v1"]["chat"]["owner"]
    # This should be in "+27xxxxxxxxx" format, but just in case it isn't
    msisdn = normalise_msisdn(whatsapp_contact_id)
    async_create_flow_start.delay(
        extra={},
        flow=settings.RAPIDPRO_EDD_LABEL_FLOW,
        urns=[f"whatsapp:{msisdn.lstrip('+')}"],
    )


def handle_event(event):
    """
    Triggers all the actions that are required for this event
    """
    if event.is_message_expired_error or event.is_whatsapp_failed_delivery_event:
        handle_whatsapp_delivery_error(event)

    if event.is_hsm_error:
        handle_whatsapp_hsm_error(event)


def handle_whatsapp_delivery_error(event):
    if not event.fallback_channel:
        async_handle_whatsapp_delivery_error.delay(f"whatsapp:{event.recipient_id}")
    else:
        df = DeliveryFailures.objects.get(contact_id=event.recipient_id)
        df.number_of_failures += 1
        df.save()

        if df.number_of_failures >= 5:
            async_create_flow_start.delay(
                extra={
                    "optout_reason": "sms_failure",
                    "timestamp": event.timestamp.timestamp(),
                },
                flow=settings.RAPIDPRO_OPTOUT_FLOW,
                urns=[f"whatsapp:{event.recipient_id}"],
            )


def handle_whatsapp_hsm_error(event):
    if settings.ENABLE_UNSENT_EVENT_ACTION:
        async_create_flow_start.delay(
            extra={
                "popi_ussd": settings.POPI_USSD_CODE,
                "optout_ussd": settings.OPTOUT_USSD_CODE,
                "timestamp": event.timestamp.timestamp(),
            },
            flow=settings.RAPIDPRO_UNSENT_EVENT_FLOW,
            urns=[f"whatsapp:{event.recipient_id}"],
        )
