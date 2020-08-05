import json
from datetime import datetime
from urllib.parse import urljoin

import phonenumbers
import pytz
import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import dateparse, translation
from django_redis import get_redis_connection
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError

from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    DeliveryFailure,
    EddSwitch,
    Event,
    IdentificationSwitch,
    LanguageSwitch,
    Message,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)
from ndoh_hub.celery import app
from ndoh_hub.utils import get_today, rapidpro
from registrations.tasks import request_to_jembi_api


def get_utc_now():
    return datetime.now(tz=pytz.utc)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def async_create_flow_start(extra, **kwargs):
    return rapidpro.create_flow_start(extra=extra, **kwargs)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def update_rapidpro_contact(urn, fields):
    rapidpro.update_contact(urn, fields=fields)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=1,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_rapidpro_contact_by_uuid(contact_uuid):
    if not contact_uuid:
        return
    return (
        rapidpro.get_contacts(uuid=contact_uuid)
        .first(retry_on_rate_exceed=True)
        .serialize()
    )


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_rapidpro_contact_by_msisdn(context, field):
    context["contact"] = (
        rapidpro.get_contacts(urn=f"whatsapp:{context[field]}")
        .first(retry_on_rate_exceed=True)
        .serialize()
    )
    return context


@app.task(acks_late=True, soft_time_limit=10, time_limit=15, bind=True)
def send_helpdesk_response_to_dhis2(self, context):
    encdate = datetime.utcfromtimestamp(int(context["inbound_timestamp"]))
    repdate = datetime.utcfromtimestamp(int(context["reply_timestamp"]))

    msisdn = phonenumbers.parse(context["inbound_address"], "ZA")
    msisdn = phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
    contact = context["contact"]

    request_to_jembi_api.delay(
        "helpdesk",
        {
            "encdate": encdate.strftime("%Y%m%d%H%M%S"),
            "repdate": repdate.strftime("%Y%m%d%H%M%S"),
            "mha": 1,  # Praekelt
            "swt": 4,  # WhatsApp
            "cmsisdn": msisdn,
            "dmsisdn": msisdn,
            "faccode": contact.get("fields", {}).get("facility_code"),
            "data": {
                "question": context["inbound_text"],
                "answer": context["reply_text"],
            },
            "class": ",".join(context["inbound_labels"]) or "Unclassified",
            "type": 7,  # Helpdesk
            "op": str(context["reply_operator"]),
            "eid": self.request.id,
            "sid": contact.get("uuid"),
        },
    )


@app.task(
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=True,
    max_retries=1,
    acks_late=True,
    soft_time_limit=60 * 60,
    time_limit=60 * 61,
)
def delete_contact_pii(contact):
    try:
        contact_uuid = contact["uuid"]
    except (TypeError, KeyError):
        return

    MSISDNSwitch.objects.filter(contact_id=contact_uuid).update(
        old_msisdn="", new_msisdn="", data={}
    )
    IdentificationSwitch.objects.filter(contact_id=contact_uuid).update(
        old_id_number="",
        new_id_number="",
        old_passport_number="",
        new_passport_number="",
        data={},
    )
    CHWRegistration.objects.filter(contact_id=contact_uuid).update(
        id_number="", passport_number="", data={}
    )
    PrebirthRegistration.objects.filter(contact_id=contact_uuid).update(
        id_number="", passport_number="", data={}
    )
    PostbirthRegistration.objects.filter(contact_id=contact_uuid).update(
        id_number="", passport_number="", data={}
    )
    OptOut.objects.filter(contact_id=contact_uuid).update(data={})
    BabySwitch.objects.filter(contact_id=contact_uuid).update(data={})
    ChannelSwitch.objects.filter(contact_id=contact_uuid).update(data={})
    LanguageSwitch.objects.filter(contact_id=contact_uuid).update(data={})
    ResearchOptinSwitch.objects.filter(contact_id=contact_uuid).update(data={})
    PublicRegistration.objects.filter(contact_id=contact_uuid).update(data={})
    PMTCTRegistration.objects.filter(contact_id=contact_uuid).update(data={})
    EddSwitch.objects.filter(contact_id=contact_uuid).update(data={})
    BabyDobSwitch.objects.filter(contact_id=contact_uuid).update(data={})

    try:
        _, msisdn = contact["urns"][0].split(":")
        msisdn = msisdn.lstrip("+")
    except (KeyError, IndexError, ValueError, AttributeError):
        return contact_uuid

    Message.objects.filter(contact_id=msisdn).update(contact_id=contact_uuid, data={})
    Event.objects.filter(recipient_id=msisdn).update(recipient_id=contact_uuid)
    return contact_uuid


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=1,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def delete_rapidpro_contact_by_uuid(contact_uuid):
    if not contact_uuid:
        return
    return rapidpro.delete_contact(contact_uuid)


forget_contact = (
    get_rapidpro_contact_by_uuid.s()
    | delete_contact_pii.s()
    | delete_rapidpro_contact_by_uuid.s()
)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_rapidpro_contact_by_urn(urn):
    context = {}
    if urn:
        redis = get_redis_connection("redis")
        _, msisdn = urn.split(":")
        key = f"hub_handle_whatsapp_delivery_error_{msisdn}"

        lock = redis.lock(key, 3600)
        if lock.acquire(blocking=False):
            context["key"] = key
            contact = rapidpro.get_contacts(urn=urn).first(retry_on_rate_exceed=True)

            if contact:
                context["contact"] = contact.serialize()

    return context


@app.task(
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=False,
    max_retries=1,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def check_contact_timestamp(context):
    contact = context.get("contact")
    if not contact:
        return context

    timestamp = contact["fields"].get("whatsapp_undelivered_timestamp")
    current_date = get_utc_now()

    send = False
    if timestamp:
        last_date = dateparse.parse_datetime(timestamp)
        if (current_date - last_date).days >= settings.WHATSAPP_EXPIRY_SMS_BOUNCE_DAYS:
            send = True
    else:
        send = True

    language = contact.get("language") or "eng"
    context = {"language": f"{language.lower()}-ZA"}
    if send:
        try:
            _, msisdn = contact["urns"][0].split(":")
            context["msisdn"] = msisdn.lstrip("+")
        except (KeyError, IndexError, ValueError, AttributeError):
            pass
    else:
        pass

    return context


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def send_undelivered_sms(context):
    if "msisdn" not in context:
        return context

    headers = {
        "Authorization": "Bearer {}".format(settings.TURN_TOKEN),
        "Content-Type": "application/json",
        "x-turn-fallback-channel": "1",
    }

    with translation.override(context["language"]):
        text = translation.ugettext(
            "We see that your MomConnect WhatsApp messages are not being "
            "delivered. If you would like to receive your messages over "
            "SMS, reply ‘SMS’."
        )

    data = json.dumps(
        {
            "preview_url": False,
            "recipient_type": "individual",
            "to": context["msisdn"],
            "type": "text",
            "text": {"body": text},
        }
    )

    r = requests.post(
        urljoin(settings.TURN_URL, "v1/messages"), headers=headers, data=data
    )
    r.raise_for_status()

    return context


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def update_rapidpro_contact_error_timestamp(context):
    if "msisdn" in context:
        msisdn = context["msisdn"]
        rapidpro.update_contact(
            f"whatsapp:{msisdn}",
            fields={"whatsapp_undelivered_timestamp": get_utc_now().isoformat()},
        )

    if "key" in context:
        redis = get_redis_connection("redis")
        redis.delete(context["key"])


async_handle_whatsapp_delivery_error = (
    get_rapidpro_contact_by_urn.s()
    | check_contact_timestamp.s()
    | send_undelivered_sms.s()
    | update_rapidpro_contact_error_timestamp.s()
)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def mark_turn_contact_healthcheck_complete(msisdn):
    if settings.HC_TURN_URL is None or settings.HC_TURN_TOKEN is None:
        return
    contact_id = msisdn.lstrip("+")
    url = urljoin(settings.HC_TURN_URL, f"v1/contacts/{contact_id}/profile")
    response = requests.patch(
        url,
        json={"healthcheck_completed": True},
        headers={
            "Authorization": f"Bearer {settings.HC_TURN_TOKEN}",
            "Accept": "application/vnd.v1+json",
        },
    )
    response.raise_for_status()


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def archive_turn_conversation(urn, message_id, reason):
    headers = {
        "Authorization": "Bearer {}".format(settings.TURN_TOKEN),
        "Accept": "application/vnd.v1+json",
        "Content-Type": "application/json",
    }

    data = json.dumps({"before": message_id, "reason": reason})

    r = requests.post(
        urljoin(settings.TURN_URL, f"v1/chats/{urn}/archive"),
        headers=headers,
        data=data,
    )
    r.raise_for_status()


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=600,
    time_limit=600,
)
def handle_expired_helpdesk_contacts():
    for contact_batch in rapidpro.get_contacts(
        group="Waiting for helpdesk"
    ).iterfetches(retry_on_rate_exceed=True):
        for contact in contact_batch:
            if contact.fields.get("helpdesk_timeout") and contact.fields.get(
                "helpdesk_message_id"
            ):
                timeout_date = datetime.strptime(
                    contact.fields["helpdesk_timeout"], "%Y-%m-%d"
                ).date()

                delta = get_today() - timeout_date
                if delta.days > settings.HELPDESK_TIMEOUT_DAYS:
                    update_rapidpro_contact.delay(
                        contact.uuid,
                        {
                            "helpdesk_timeout": None,
                            "wait_for_helpdesk": None,
                            "helpdesk_message_id": None,
                        },
                    )

                    wa_id = None
                    for urn in contact.urns:
                        if "whatsapp" in urn:
                            wa_id = urn.split(":")[1]

                    if wa_id:
                        archive_turn_conversation.delay(
                            wa_id,
                            contact.fields["helpdesk_message_id"],
                            f"Auto archived after {delta.days} days",
                        )


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=False,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def reset_delivery_failure(contact_uuid):
    contact = rapidpro.get_contacts(uuid=contact_uuid).first(retry_on_rate_exceed=True)
    if not contact:
        return

    wa_id = None
    for urn in contact.urns:
        if "whatsapp" in urn:
            wa_id = urn.split(":")[1]

    if wa_id:
        DeliveryFailure.objects.filter(contact_id=wa_id).update(number_of_failures=0)
