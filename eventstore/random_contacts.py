import pytz
import requests
from urllib.parse import urljoin
from django.conf import settings
from ndoh_hub.celery import app
from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError
import datetime
from ndoh_hub.utils import rapidpro, get_today


if settings.EXTERNAL_REGISTRATIONS_V2:
    if settings.TURN_URL and settings.TURN_TOKEN:
        turn_api = settings.TURN_URL + "/v1/contacts/{}/messages"
        turn_header = {
            "Authorization": "Bearer {}".format(settings.TURN_TOKEN),
            "Accept": "application/vnd.v1+json",
        }

    if settings.RAPIDPRO_URL and settings.RAPIDPRO_TOKEN:
        rapidpro_url = urljoin(settings.RAPIDPRO_URL, "/contact/read/{}/")


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, TembaHttpError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_contacts():
    # modified before and after datetime
    before = get_today()
    after = get_today() - datetime.timedelta(days=6)
    contact_details = []
    try:
        for contact_batch in rapidpro.get_contacts(
            before=before, after=after
        ).iterfetches(retry_on_rate_exceed=True):
            for contact in contact_batch:
                contact_uuid = contact.uuid
                contact_urns = contact.urns

                if contact_uuid and contact_urns:
                    whatsapp_number = [
                        i.split(":")[1] for i in contact_urns if "whatsapp" in i
                    ]

                    if whatsapp_number:
                        contact = whatsapp_number[0]
                        profile_link = get_turn_profile_link(contact)

                        if profile_link:
                            rapidpro_link = rapidpro_url.format(contact_uuid)
                            links = {
                                "Rapid Pro Link: ": rapidpro_link,
                                "Turn Link": profile_link,
                            }

                            contact_details.append(links)

        if contact_details:
            sent = send_slack_message(contact_details)
            return {"success": sent, "results": contact_details}
        return {"success": False, "results": contact_details}
    except Exception as e:
        return {"success": False, "results": contact_details}


def get_turn_profile_link(contact):
    turn_link = None

    if contact:
        try:
            turn_url = turn_api.format(contact)

            profile = requests.get(url=turn_url, headers=turn_header)

            if profile:
                # Get turn message link
                turn_link = profile.json().get("chat").get("permalink")
        except Exception as e:
            return turn_link
    return turn_link


def send_slack_message(contact_details):
    # Send message to slack
    try:
        response = requests.post(
            urljoin(settings.SLACK_URL, "/api/chat.postMessage"),
            {
                "token": settings.SLACK_TOKEN,
                "channel": "test-mon",
                "text": contact_details,
            },
        ).json()
        if response:
            if response["ok"]:
                return True
            return False
    except Exception as e:
        return False


if __name__ == "__main__":
    get_contacts()
