from __future__ import absolute_import, division

import base64
import datetime
import hmac
import json
import random
from hashlib import sha256
from urllib.parse import urljoin

import phonenumbers
import pkg_resources
import requests
import six
from django.conf import settings
from django_redis import get_redis_connection
from rest_framework.exceptions import AuthenticationFailed
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.message_sender import MessageSenderApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient
from temba_client.v2 import TembaClient
from wabclient import Client as WABClient

from ndoh_hub.auth import CachedTokenAuthentication
from ndoh_hub.constants import (  # noqa:F401
    ID_TYPES,
    JEMBI_LANGUAGES,
    LANGUAGES,
    PASSPORT_ORIGINS,
    WHATSAPP_LANGUAGE_MAP,
)

sbm_client = StageBasedMessagingApiClient(
    api_url=settings.STAGE_BASED_MESSAGING_URL,
    auth_token=settings.STAGE_BASED_MESSAGING_TOKEN,
)

is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL, auth_token=settings.IDENTITY_STORE_TOKEN
)

ms_client = MessageSenderApiClient(
    api_url=settings.MESSAGE_SENDER_URL, auth_token=settings.MESSAGE_SENDER_TOKEN
)

wab_client = WABClient(url=settings.ENGAGE_URL)
wab_client.connection.set_token(settings.ENGAGE_TOKEN)

rapidpro = None
if settings.EXTERNAL_REGISTRATIONS_V2:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)

VERSION = pkg_resources.require("ndoh-hub")[0].version

redis = get_redis_connection("redis")


def get_identity_msisdn(registrant_id):
    """
    Given an identity UUID, returns the msisdn for the identity. Takes into
    account default addresses, opted out addresses, and missing identities
    or addresses. Returns None when it cannot find an MSISDN address.
    """
    identity = is_client.get_identity(registrant_id)
    if not identity:
        return

    msisdns = identity["details"].get("addresses", {}).get("msisdn", {})

    identity_msisdn = None
    for msisdn, details in msisdns.items():
        if "default" in details and details["default"]:
            return msisdn
        if not ("optedout" in details and details["optedout"]):
            identity_msisdn = msisdn
    return identity_msisdn


def validate_signature(request):
    secret = settings.TURN_HMAC_SECRET
    try:
        signature = request.META["HTTP_X_TURN_HOOK_SIGNATURE"]
    except KeyError:
        raise AuthenticationFailed("X-Turn-Hook-Signature header required")

    h = hmac.new(secret.encode(), request.body, sha256)

    if not hmac.compare_digest(base64.b64encode(h.digest()).decode(), signature):
        raise AuthenticationFailed("Invalid hook signature")


def is_valid_uuid(id):
    return len(id) == 36 and id[14] == "4" and id[19] in ["a", "b", "8", "9"]


def is_valid_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
        return True
    except Exception:
        return False


def is_valid_edd_date(edd):
    """
    Checks given Estimated Due Date is in the future but not more than
    9 months away
    """
    return edd > get_today() and edd < get_today() + datetime.timedelta(weeks=43)


def is_valid_edd(date):
    """
    Checks given Estimated Due Date is in the future but not more than
    9 months away
    """
    if is_valid_date(date):
        edd = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return is_valid_edd_date(edd)
    return False


def is_valid_baby_dob_date(dob: datetime.date) -> bool:
    """
    Checks given baby date of birth is in the past but not more than 2 years old
    """
    return dob < get_today() and dob > get_today() - datetime.timedelta(days=365 * 2)


def is_valid_lang(lang):
    return lang in LANGUAGES


# TODO 15: Improve validation functions
def is_valid_msisdn(msisdn):
    """A very basic msisdn validation check"""
    return msisdn[0] == "+" and len(msisdn) == 12


def is_valid_faccode(faccode):
    """A very basic faccode validation check"""
    return len(faccode) >= 1


def is_valid_sanc_no(sanc_no):
    """A very basic sanc_no validation check"""
    return len(sanc_no) >= 1


def is_valid_persal_no(persal_no):
    """A very basic persal_no validation check"""
    return len(persal_no) >= 1


def is_valid_sa_id_no(sa_id_no):
    """A very basic sa_id_no validation check"""
    return len(sa_id_no) == 13


def is_valid_passport_no(passport_no):
    """A very basic passport_no validation check"""
    return len(passport_no) >= 1


def is_valid_passport_origin(passport_origin):
    """A passport_origin validation check"""
    return passport_origin in PASSPORT_ORIGINS


def is_valid_id_type(id_type):
    """A ID type check"""
    return id_type in ID_TYPES


def get_today():
    return datetime.date.today()


def get_mom_age(today, mom_dob):
    """Calculate the mother's age in years"""
    born = datetime.datetime.strptime(mom_dob, "%Y-%m-%d")
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def get_available_metrics():
    available_metrics = []
    available_metrics.extend(settings.METRICS_REALTIME)
    available_metrics.extend(settings.METRICS_SCHEDULED)
    return available_metrics


def json_decode(data):
    """
    Decodes the given JSON as primitives
    """
    if isinstance(data, six.binary_type):
        data = data.decode("utf-8")

    return json.loads(data)


def normalise_msisdn(msisdn: str) -> str:
    """
    Takes the MSISDN input, and normalises it to E164 format
    """
    return phonenumbers.format_number(
        phonenumbers.parse(msisdn, "ZA"), phonenumbers.PhoneNumberFormat.E164
    )


class TokenAuthQueryString(CachedTokenAuthentication):
    """
    Look for the token in the querystring parameter "token"
    """

    def authenticate(self, request):
        token = request.query_params.get("token", None)
        if token is not None:
            return self.authenticate_credentials(token)
        return None


def get_random_date():
    start_date = datetime.date(2020, 1, 1)
    end_date = datetime.date.today()

    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days

    random_number_of_days = random.randrange(days_between_dates)

    return start_date + datetime.timedelta(days=random_number_of_days)


def send_slack_message(channel, text):
    # Send message to slack
    if settings.SLACK_URL and settings.SLACK_TOKEN:
        response = requests.post(
            urljoin(settings.SLACK_URL, "/api/chat.postMessage"),
            {"token": settings.SLACK_TOKEN, "channel": channel, "text": text},
        ).json()

        if response:
            if response["ok"]:
                return True
            return False
    return False
