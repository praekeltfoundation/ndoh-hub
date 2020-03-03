from celery import chain
from django.conf import settings
from django.db.models import F

from changes.tasks import get_engage_inbound_and_reply
from eventstore.models import DeliveryFailure, OptOut
from eventstore.tasks import (
    async_create_flow_start,
    async_handle_whatsapp_delivery_error,
    get_rapidpro_contact_by_msisdn,
    send_helpdesk_response_to_dhis2,
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

    if event.fallback_channel is True:
        handle_fallback_event(event)


def handle_fallback_event(event):
    if event.status == "failed":
        try:
            df = DeliveryFailure.objects.get(contact_id=event.recipient_id)
            df.number_of_failures = F("number_of_failures") + 1
            df.save()
            df.refresh_from_db()

            if df.number_of_failures >= 5:
                async_create_flow_start.delay(
                    extra={
                        "optout_reason": OptOut.SMS_FAILURE_REASON,
                        "timestamp": event.timestamp.timestamp(),
                        "babyloss_subscription": "FALSE",
                        "delete_info_for_babyloss": "FALSE",
                        "delete_info_consent": "FALSE",
                        "source": "System",
                    },
                    flow=settings.RAPIDPRO_OPTOUT_FLOW,
                    urns=[f"whatsapp:{event.recipient_id}"],
                )
        except DeliveryFailure.DoesNotExist:
            df = DeliveryFailure(contact_id=event.recipient_id, number_of_failures=1)
            df.save()
    else:
        df = DeliveryFailure(contact_id=event.recipient_id, number_of_failures=0)
        df.save()


def handle_whatsapp_delivery_error(event):
    async_handle_whatsapp_delivery_error.delay(f"whatsapp:{event.recipient_id}")


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
