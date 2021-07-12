import json
import logging
from datetime import date, datetime
from urllib.parse import urljoin

import phonenumbers
import pytz
import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError

from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    DeliveryFailure,
    EddSwitch,
    Event,
    IdentificationSwitch,
    ImportError,
    ImportRow,
    LanguageSwitch,
    Message,
    MomConnectImport,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)
from ndoh_hub.celery import app
from ndoh_hub.utils import get_mom_age, get_today, rapidpro
from registrations.models import ClinicCode
from registrations.tasks import request_to_jembi_api

logger = logging.getLogger(__name__)


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


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=5,
    acks_late=True,
    soft_time_limit=600,
    time_limit=700,
)
def validate_momconnect_import(mcimport_id):
    mcimport = MomConnectImport.objects.get(id=mcimport_id)

    if mcimport.status != MomConnectImport.Status.VALIDATING:
        return

    for row in mcimport.rows.iterator():
        msisdn = phonenumbers.parse(row.msisdn, "ZA")
        msisdn = phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
        urn = f"whatsapp:{msisdn.lstrip('+')}"
        contact = rapidpro.get_contacts(urn=urn).first(retry_on_rate_exceed=True)

        if contact is None:
            # No existing contact, so nothing to validate
            continue

        # validate previously opted out
        if (
            contact.fields.get("opted_out")
            and contact.fields["opted_out"].strip().lower() == "true"
            and not row.previous_optout
        ):
            mcimport.status = MomConnectImport.Status.ERROR
            mcimport.save()
            mcimport.errors.create(
                row_number=row.row_number,
                error_type=ImportError.ErrorType.OPTED_OUT_ERROR,
                error_args=[],
            )
            continue

        # validate already receiving prebirth messaging
        try:
            prebirth_messaging = int(contact.fields.get("prebirth_messaging"))
        except (TypeError, ValueError):
            prebirth_messaging = -1
        if prebirth_messaging >= 1 and prebirth_messaging <= 6:
            mcimport.status = MomConnectImport.Status.ERROR
            mcimport.save()
            mcimport.errors.create(
                row_number=row.row_number,
                error_type=ImportError.ErrorType.ALREADY_REGISTERED,
                error_args=[],
            )
            continue

    if mcimport.status == MomConnectImport.Status.VALIDATING:
        mcimport.status = MomConnectImport.Status.VALIDATED
        mcimport.save()
        upload_momconnect_import.delay(mcimport.id)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=5,
    acks_late=True,
    soft_time_limit=600,
    time_limit=700,
)
def upload_momconnect_import(mcimport_id):
    mcimport = MomConnectImport.objects.get(id=mcimport_id)

    if mcimport.status != MomConnectImport.Status.VALIDATED:
        return

    mcimport.status = MomConnectImport.Status.UPLOADING
    mcimport.save()

    for row in (
        mcimport.rows.order_by("row_number")
        .filter(row_number__gt=mcimport.last_uploaded_row)
        .iterator()
    ):
        flow_uuid = settings.RAPIDPRO_PREBIRTH_CLINIC_FLOW

        msisdn = phonenumbers.parse(row.msisdn, "ZA")
        msisdn = phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
        urn = f"whatsapp:{msisdn.lstrip('+')}"
        data = {
            "research_consent": "TRUE" if row.research_consent else "FALSE",
            "registered_by": msisdn,
            "language": {
                ImportRow.Language.ZUL: "zul",
                ImportRow.Language.XHO: "xho",
                ImportRow.Language.AFR: "afr",
                ImportRow.Language.ENG: "eng",
                ImportRow.Language.NSO: "nso",
                ImportRow.Language.TSN: "tsn",
                ImportRow.Language.SOT: "sot",
                ImportRow.Language.TSO: "tso",
                ImportRow.Language.SSW: "ssw",
                ImportRow.Language.VEN: "ven",
                ImportRow.Language.NBL: "nbl",
            }[row.language],
            "timestamp": datetime.now().isoformat(),
            "source": mcimport.source,
            "id_type": {
                ImportRow.IDType.SAID: "sa_id",
                ImportRow.IDType.PASSPORT: "passport",
                ImportRow.IDType.NONE: "dob",
            }[row.id_type],
            "clinic_code": row.facility_code,
            "sa_id_number": row.id_number,
            "passport_number": row.passport_number,
            "swt": "7",
        }

        if row.edd_year and row.edd_month and row.edd_day:
            data["edd"] = date(row.edd_year, row.edd_month, row.edd_day).isoformat()

        if row.baby_dob_year and row.baby_dob_month and row.baby_dob_day:
            data["baby_dob"] = date(
                row.baby_dob_year, row.baby_dob_month, row.baby_dob_day
            ).isoformat()
            flow_uuid = settings.RAPIDPRO_POSTBIRTH_CLINIC_FLOW

        if row.passport_country is not None:
            data["passport_origin"] = {
                ImportRow.PassportCountry.ZW: "zw",
                ImportRow.PassportCountry.MZ: "mz",
                ImportRow.PassportCountry.MW: "mw",
                ImportRow.PassportCountry.NG: "ng",
                ImportRow.PassportCountry.CD: "cd",
                ImportRow.PassportCountry.SO: "so",
                ImportRow.PassportCountry.OTHER: "other",
            }[row.passport_country]
        if row.dob_year and row.dob_month and row.dob_day:
            data["dob"] = date(row.dob_year, row.dob_month, row.dob_day).isoformat()

        rapidpro.create_flow_start(flow=flow_uuid, urns=[urn], extra=data)
        mcimport.last_uploaded_row = row.row_number
        mcimport.save()

    mcimport.status = MomConnectImport.Status.COMPLETE
    mcimport.save()


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=20,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def process_ada_assessment_notification(
    username, id, patient_id, patient_dob, observations, timestamp
):
    contact = rapidpro.get_contacts(uuid=patient_id).first(retry_on_rate_exceed=True)
    if not contact or not contact.urns or not contact.fields.get("facility_code"):
        # Contact doesn't exist, or we don't have a full clinic registration, so ignore
        # the notification
        logger.info(f"Cannot find contact with UUID {patient_id}, skipping processing")
        return

    try:
        cliniccode = ClinicCode.objects.get(value=contact.fields["facility_code"])
    except ClinicCode.DoesNotExist:
        # We don't recognise this contact's clinic code, so ignore notification
        logger.info(
            f"Cannot find clinic code {contact.fields['facility_code']}, skipping "
            "processing"
        )
        return

    rapidpro.update_contact(contact, fields={"date_of_birth": patient_dob})

    _, msisdn = contact.urns[0].split(":")
    msisdn = f"+{msisdn.lstrip('+')}"

    age_years = get_mom_age(get_today(), patient_dob)
    if age_years < 18:
        age = Covid19Triage.AGE_U18
    elif age_years < 40:
        age = Covid19Triage.AGE_18T40
    elif age_years <= 65:
        age = Covid19Triage.AGE_40T65
    else:
        age = Covid19Triage.AGE_O65

    exposure = observations.get("possible contact with 2019 novel coronavirus")
    if exposure is True:
        exposure = Covid19Triage.EXPOSURE_YES
    elif exposure is False:
        exposure = Covid19Triage.EXPOSURE_NO
    else:
        exposure = Covid19Triage.EXPOSURE_NOT_SURE

    triage = Covid19Triage(
        deduplication_id=id,
        msisdn=msisdn,
        source="Ada",
        age=age,
        date_of_birth=patient_dob,
        province=cliniccode.province,
        city=cliniccode.name,
        city_location=cliniccode.location,
        fever=observations["fever"],
        cough=observations["cough"],
        sore_throat=observations["sore throat"],
        smell=observations.get("diminished sense of taste")
        or observations.get("reduced sense of smell"),
        muscle_pain=observations.get("generalized muscle pain"),
        difficulty_breathing=observations.get("difficulty breathing"),
        exposure=exposure,
        tracing=False,
        gender=Covid19Triage.GENDER_FEMALE,
        completed_timestamp=timestamp,
        created_by=username,
        data={
            "age": age_years,
            "pregnant": bool(contact.fields.get("prebirth_messaging")),
        },
    )
    triage.risk = triage.calculate_risk()
    triage.full_clean()
    triage.save()
