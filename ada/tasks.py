import json

import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.urls import reverse
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError

from ada.utils import rapidpro
from ndoh_hub.celery import app


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def submit_whatsappid_to_rapidpro(whatsappid):
    if rapidpro and settings.ADA_PROTOTYPE_SURVEY_FLOW_ID:
        return rapidpro.create_flow_start(
            extra={},
            flow=settings.ADA_PROTOTYPE_SURVEY_FLOW_ID,
            urns=[f"whatsapp:{whatsappid.lstrip('+')}"],
        )


def submit_whatsappid_to_rapidpro_topup(whatsappid):
    if rapidpro and settings.ADA_TOPUP_FLOW_ID:
        return rapidpro.create_flow_start(
            extra={},
            flow=settings.ADA_TOPUP_FLOW_ID,
            urns=[f"whatsapp:{whatsappid.lstrip('+')}"],
        )


def post_to_topup_endpoint(whatsappid):
    token = settings.ADA_TOPUP_AUTHORIZATION_TOKEN
    head = {"Authorization": "Token " + token, "Content-Type": "application/json"}
    payload = {"whatsappid": whatsappid}
    url = reverse("rapidpro_topup_flow")
    response = requests.post(url, data=json.dumps(payload), headers=head)
    return response
