from urllib.parse import urljoin

import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError
from temba_client.v2 import TembaClient

from ndoh_hub.celery import app

rapidpro = None
if settings.HC_RAPIDPRO_URL and settings.HC_RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.HC_RAPIDPRO_URL, settings.HC_RAPIDPRO_TOKEN)


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    max_retires=3,
    retry_backoff=True,
    soft_time_limit=15,
    time_limit=45,
    acks_late=True,
)
def update_turn_contact(msisdn, field, value):
    if settings.HC_TURN_URL is None or settings.HC_TURN_TOKEN is None:
        return
    # request should not take longer than 15 seconds total
    connect_timeout, read_timeout = 5.0, 10.0

    msisdn = msisdn.lstrip("+")

    response = requests.patch(
        url=urljoin(settings.HC_TURN_URL, f"/v1/contacts/{msisdn}/profile"),
        json={field: value},
        timeout=(connect_timeout, read_timeout),
        headers={
            "Authorization": f"Bearer {settings.HC_TURN_TOKEN}",
            "Accept": "application/vnd.v1+json",
        },
    )

    response.raise_for_status()

    return f"Finished updating contact {field}={value}."


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def start_study_c_registration_flow(
    msisdn, test_arm, quaratine_arm, pilot_arm, risk, source
):
    if rapidpro and settings.HCS_STUDY_C_REGISTRATION_FLOW_ID:
        return rapidpro.create_flow_start(
            extra={
                "hcs_risk": risk,
                "hcs_study_c_testing_arm": test_arm,
                "hcs_study_c_quarantine_arm": quaratine_arm,
                "hcs_study_c_pilot_arm": pilot_arm,
                "hcs_source": source,
            },
            flow=settings.HCS_STUDY_C_REGISTRATION_FLOW_ID,
            urns=[f"whatsapp:{msisdn.lstrip('+')}"],
        )
