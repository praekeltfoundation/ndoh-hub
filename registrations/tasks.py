from datetime import timedelta

from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from requests.exceptions import HTTPError, RequestException
from wabclient.exceptions import AddressException

from ndoh_hub import utils
from ndoh_hub.celery import app
from ndoh_hub.utils import redis

from .models import WhatsAppContact


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded, HTTPError),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def get_whatsapp_contact(msisdn):
    """
    Fetches the whatsapp contact ID from the API, and stores it in the database.
    Args:
        msisdn (str): The MSISDN to perform the lookup for.
    """
    if redis.get(f"wacontact:{msisdn}"):
        return
    with redis.lock(f"wacontact:{msisdn}", timeout=15):
        # Try to get existing
        try:
            contact = (
                WhatsAppContact.objects.filter(
                    created__gt=timezone.now() - timedelta(days=7)
                )
                .filter(msisdn=msisdn)
                .latest("created")
            )
            return contact.api_format
        except WhatsAppContact.DoesNotExist:
            pass

        # If no existing, fetch status from API and create
        try:
            whatsapp_id = utils.wab_client.get_address(msisdn)
        except AddressException:
            whatsapp_id = ""
        contact = WhatsAppContact.objects.create(msisdn=msisdn, whatsapp_id=whatsapp_id)
        return contact.api_format
