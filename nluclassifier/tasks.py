import logging
from urllib.parse import urljoin

import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from ndoh_hub.celery import app

logger = logging.getLogger(__name__)

CELERY_TASK_OPTIONS = {
    "autoretry_for": (RequestException, SoftTimeLimitExceeded),
    "retry_backoff": True,
    "max_retries": 15,
    "acks_late": True,
    "soft_time_limit": 10,
    "time_limit": 15,
}


@app.task(**CELERY_TASK_OPTIONS)
def process_feedback_for_labeling(message_id: str, inbound_message: str):
    """
    Call the NLU endpoint for feedback classification.
    LLabel the message in Turn using the detected intent.
    """

    nlu_label = None

    NLU_URL = settings.INTENT_CLASSIFIER_URL
    NLU_USER = settings.INTENT_CLASSIFIER_USER
    NLU_PASS = settings.INTENT_CLASSIFIER_PASS
    # fmt: off
    try:
        nlu_endpoint = urljoin(NLU_URL, "/nlu/feedback/")
        params = {"question": inbound_message}

        logger.info(f"Calling NLU for message {message_id} at {nlu_endpoint}")

        response = requests.get(
            nlu_endpoint,
            params=params,
            auth=HTTPBasicAuth(NLU_USER, NLU_PASS),
            timeout=CELERY_TASK_OPTIONS["soft_time_limit"],
        )
        response.raise_for_status()

        nlu_label = response.json().get("intent")

        logger.info(f"NLU Intent for {message_id}: {nlu_label}")

    except RequestException as e:
        logger.warning(
            f"NLU service failed for message {message_id}. "
            f"Retrying. Error: {e}"
            )
        raise
    except Exception as e:
        logger.error(
            f"NLU non-retriable failure for message {message_id}: "
            f"{e}"
            )
        return

    if nlu_label and nlu_label.lower() in ("compliment", "complaint"):

        TURN_TOKEN = settings.TURN_TOKEN
        TURN_URL = settings.TURN_URL

        turn_endpoint = urljoin(TURN_URL, f"v1/messages/{message_id}/labels")

        label_payload = {"labels": [nlu_label.lower()]}

        headers = {
            "Authorization": f"Bearer {TURN_TOKEN}",
            "Accept": "application/vnd.v1+json",
            "Content-Type": "application/json",
        }

        try:
            logger.info(
                f"Labeling message {message_id} in Turn at {turn_endpoint} "
                f"with label: {nlu_label}"
                )

            turn_response = requests.post(
                turn_endpoint,
                json=label_payload,
                headers=headers,
                timeout=CELERY_TASK_OPTIONS["soft_time_limit"],
            )

            turn_response.raise_for_status()

            logger.info(
                f"Successfully labeled message {message_id} "
                f"as: {nlu_label}"
                )

        except RequestException as e:

            logger.warning(
                f"Turn API failed to label message {message_id}. "
                f"Retrying. Error: {e}"
                )
            raise
        except Exception as e:
            logger.error(
                f"Turn API unrecoverable error for message {message_id}: {e}"
            )
            return
    else:
        logger.info(
            f"NLU result was '{nlu_label}' (not 'Compliment' or 'Complaint'). "
            f"No Turn label applied for message {message_id}."
            )
