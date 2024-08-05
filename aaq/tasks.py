from urllib.parse import urljoin

import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from requests.exceptions import RequestException

from ndoh_hub.celery import app


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def send_feedback_task(secret_key, inbound_id, feedback_type, **kwargs):
    data = {
        "feedback_secret_key": secret_key,
        "inbound_id": inbound_id,
        "feedback": {"feedback_type": feedback_type},
    }
    if "faq_id" in kwargs:
        data["feedback"]["faq_id"] = kwargs["faq_id"]
    if "page_number" in kwargs:
        data["feedback"]["page_number"] = kwargs["page_number"]

    url = urljoin(settings.AAQ_CORE_API_URL, "/inbound/feedback")
    headers = {
        "Authorization": settings.AAQ_CORE_INBOUND_CHECK_AUTH,
        "Content-Type": "application/json",
    }
    response = requests.request("PUT", url, json=data, headers=headers)
    response.raise_for_status()


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def send_feedback_task_v2(feedback_secret_key, query_id, content_id, **kwargs):
    data = {
        "feedback_secret_key": feedback_secret_key,
        "query_id": query_id,
        "content_id": content_id,
    }

    if "feedback_sentiment" in kwargs:
        data["feedback_sentiment"] = kwargs["feedback_sentiment"]
    if "feedback_text" in kwargs:
        data["feedback_text"] = kwargs["feedback_text"]

    url = urljoin(settings.AAQ_V2_API_URL, "/content-feedback")
    headers = {
        "Authorization": settings.AAQ_V2_AUTH,
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
