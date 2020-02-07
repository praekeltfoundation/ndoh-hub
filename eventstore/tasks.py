from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import RequestException

from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
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
from ndoh_hub.utils import rapidpro


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def async_create_flow_start(extra, **kwargs):
    return rapidpro.create_flow_start(extra=extra, **kwargs)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def update_rapidpro_contact(urn, fields):
    rapidpro.update_contact(urn, fields=fields)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
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

    try:
        _, msisdn = contact["urns"][0].split(":")
        msisdn = msisdn.lstrip("+")
    except (KeyError, IndexError, ValueError, AttributeError):
        return contact_uuid

    Message.objects.filter(contact_id=msisdn).update(contact_id=contact_uuid, data={})
    Event.objects.filter(recipient_id=msisdn).update(recipient_id=contact_uuid)
    return contact_uuid


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
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
