from celery import chain
from django.conf import settings

from eventstore.models import DeliveryFailure, Event, OptOut
from eventstore.tasks import (
    async_create_flow_start,
    get_rapidpro_contact_by_msisdn,
    send_helpdesk_response_to_dhis2,
    update_rapidpro_contact,
)
from ndoh_hub.utils import normalise_msisdn

from .tasks import get_engage_inbound_and_reply


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
    # Submit to Jembi
    chain(
        get_engage_inbound_and_reply.s(),
        get_rapidpro_contact_by_msisdn.s("inbound_address"),
        send_helpdesk_response_to_dhis2.s(),
    ).delay(whatsapp_contact_id, message.id)

    # Clear the wait_for_helpdesk flag
    update_rapidpro_contact.delay(
        f"whatsapp:{msisdn.lstrip('+')}", {"wait_for_helpdesk": ""}
    )


def handle_inbound(message):
    """
    Triggers all the actions that are required for this inbound message
    """
    if not message.fallback_channel:
        update_rapidpro_preferred_channel(message)

    if not settings.DISABLE_EDD_LABEL_FLOW and message.has_label("EDD ISSUE"):
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
    if event.status == Event.FAILED:
        reason = OptOut.WHATSAPP_FAILURE_REASON
        if event.fallback_channel is True:
            reason = OptOut.SMS_FAILURE_REASON

            if settings.DISABLE_SMS_FAILURE_OPTOUTS:
                return

        df, created = DeliveryFailure.objects.get_or_create(
            contact_id=event.recipient_id, defaults={"number_of_failures": 0}
        )

        if not created and (event.timestamp - df.timestamp).days <= 0:
            return

        df.number_of_failures += 1
        df.save()
        if df.number_of_failures == 5:
            async_create_flow_start.delay(
                extra={
                    "optout_reason": reason,
                    "timestamp": event.timestamp.timestamp(),
                    "babyloss_subscription": "FALSE",
                    "delete_info_for_babyloss": "FALSE",
                    "delete_info_consent": "FALSE",
                    "source": "System",
                },
                flow=settings.RAPIDPRO_OPTOUT_FLOW,
                urns=[f"whatsapp:{event.recipient_id}"],
            )

    elif event.status == Event.READ or event.status == Event.DELIVERED:
        DeliveryFailure.objects.update_or_create(
            contact_id=event.recipient_id, defaults={"number_of_failures": 0}
        )
