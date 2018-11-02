import datetime
import json
from unittest import mock

import responses
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_hooks.models import model_saved

from ndoh_hub import utils, utils_tests
from registrations.models import Registration, Source, SubscriptionRequest
from registrations.signals import psh_fire_created_metric, psh_validate_subscribe

from .models import Change
from .signals import psh_validate_implement
from .tasks import (
    remove_personally_identifiable_fields,
    restore_personally_identifiable_fields,
    validate_implement,
)

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def override_get_today():
    return datetime.datetime.strptime("20150817", "%Y%m%d").date()


def mock_get_active_subs_mcpre_mcpost_pmtct_nc(registrant_id):
    pmtct_prebirth_sub_id = "subscriptionid-pmtct-prebirth-000000"
    momconnect_prebirth_sub_id = "subscriptionid-momconnect-prebirth-0"
    nurseconnect_sub_id = "subscriptionid-nurseconnect-00000000"
    momconnect_postbirth_sub_id = "subscriptionid-momconnect-postbirth-"
    responses.add(
        responses.GET,
        "http://sbm/api/v1/subscriptions/?active=True&identity={}".format(
            registrant_id
        ),
        json={
            "next": None,
            "previous": None,
            "results": [
                {  # pmtct_prebirth.patient.1 subscription
                    "id": pmtct_prebirth_sub_id,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/{}".format(
                        pmtct_prebirth_sub_id
                    ),
                    "messageset": 11,
                    "next_sequence_number": 11,
                    "schedule": 101,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {  # momconnect_prebirth.hw_full.1 subscription
                    "id": momconnect_prebirth_sub_id,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/{}".format(
                        momconnect_prebirth_sub_id
                    ),
                    "messageset": 21,
                    "next_sequence_number": 21,
                    "schedule": 121,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {  # nurseconnect.hw_full.1 subscription
                    "id": nurseconnect_sub_id,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/{}".format(
                        nurseconnect_sub_id
                    ),
                    "messageset": 61,
                    "next_sequence_number": 6,
                    "schedule": 161,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {  # momconnect_postbirth.hw_full.1 subscription
                    "id": momconnect_postbirth_sub_id,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/{}".format(
                        momconnect_postbirth_sub_id
                    ),
                    "messageset": 32,
                    "next_sequence_number": 32,
                    "schedule": 132,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
            ],
        },
        status=200,
        content_type="application/json",
        match_querystring=True,
    )

    return [
        pmtct_prebirth_sub_id,
        momconnect_prebirth_sub_id,
        nurseconnect_sub_id,
        momconnect_postbirth_sub_id,
    ]


def mock_get_active_subs_whatsapp(registrant_id, messagesets):
    whatsapp_prebirth_sub_id = "subscriptionid-whatsapp-prebirth-0"
    responses.add(
        responses.GET,
        "http://sbm/api/v1/subscriptions/?active=True&identity={}".format(
            registrant_id
        ),
        json={
            "next": None,
            "previous": None,
            "results": [
                {  # whatsapp_momconnect_prebirth.hw_full.1 subscription
                    "id": whatsapp_prebirth_sub_id,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/{}".format(
                        whatsapp_prebirth_sub_id
                    ),
                    "messageset": messageset,
                    "next_sequence_number": 21,
                    "schedule": 121,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                }
                for messageset in messagesets
            ],
        },
        status=200,
        content_type="application/json",
        match_querystring=True,
    )

    return whatsapp_prebirth_sub_id


def mock_get_messagesets(messagesets):
    """
    Mocks the request for getting the list of messagesets using responses.
    `messagesets` is a list of short names for the messagesets that should be
    returned.
    """
    response = [
        {
            "id": i,
            "short_name": short_name,
            "content_type": "text",
            "notes": "",
            "next_set": 7,
            "default_schedule": 1,
            "created_at": "2015-07-10T06:13:29.693272Z",
            "updated_at": "2015-07-10T06:13:29.693272Z",
        }
        for i, short_name in enumerate(messagesets)
    ]
    responses.add(
        responses.GET,
        "http://sbm/api/v1/messageset/",
        status=200,
        json={"next": None, "previous": None, "results": response},
        content_type="application/json",
    )


def mock_get_messageset(messageset_id, short_name):
    responses.add(
        responses.GET,
        "http://sbm/api/v1/messageset/{}/".format(messageset_id),
        json={
            "id": messageset_id,
            "short_name": short_name,
            "content_type": "text",
            "notes": "",
            "next_set": 7,
            "default_schedule": 1,
            "created_at": "2015-07-10T06:13:29.693272Z",
            "updated_at": "2015-07-10T06:13:29.693272Z",
        },
        status=200,
        content_type="application/json",
    )


def mock_search_messageset(messageset_id, short_name):
    responses.add(
        responses.GET,
        "http://sbm/api/v1/messageset/?short_name={}".format(short_name),
        json={
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": messageset_id,
                    "short_name": short_name,
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                }
            ],
        },
        status=200,
        content_type="application/json",
        match_querystring=True,
    )


def mock_get_all_messagesets():
    responses.add(
        responses.GET,
        "http://sbm/api/v1/messageset/",
        json={
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": 21,
                    "short_name": "momconnect_prebirth.hw_full.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {
                    "id": 61,
                    "short_name": "nurseconnect.hw_full.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {
                    "id": 62,
                    "short_name": "nurseconnect_childm.hw_full.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {
                    "id": 11,
                    "short_name": "pmtct_prebirth.patient.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {
                    "id": 98,
                    "short_name": "whatsapp_momconnect_prebirth.hw_full.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
                {
                    "id": 99,
                    "short_name": "whatsapp_pmtct_prebirth.hw_full.1",
                    "content_type": "text",
                    "notes": "",
                    "next_set": 7,
                    "default_schedule": 1,
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z",
                },
            ],
        },
        status=200,
        content_type="application/json",
        match_querystring=True,
    )


def mock_get_subscriptions(querystring=None, results=[]):
    """
    Uses responses to mock the request for getting a list of subscriptions.
    `querystring` is the querystring to use for filtering
    `results` is the list of subscriptions returned in the response
    """
    url = "http://sbm/api/v1/subscriptions/{}".format(querystring)
    responses.add(
        responses.GET,
        url,
        json={"next": None, "previous": None, "results": results},
        status=200,
        content_type="application/json",
        match_querystring=bool(querystring),
    )


def mock_get_active_subs_mc(registrant_id):
    momconnect_prebirth_sub_id = "subscriptionid-momconnect-prebirth-0"
    mock_get_subscriptions(
        "?active=True&identity={}".format(registrant_id),
        [
            {  # momconnect_prebirth.hw_full.1 subscription
                "id": momconnect_prebirth_sub_id,
                "identity": registrant_id,
                "active": True,
                "completed": False,
                "lang": "eng_ZA",
                "url": "http://sbm/api/v1/subscriptions/{}".format(
                    momconnect_prebirth_sub_id
                ),
                "messageset": 21,
                "next_sequence_number": 21,
                "schedule": 121,
                "process_status": 0,
                "version": 1,
                "metadata": {},
                "created_at": "2015-07-10T06:13:29.693272Z",
                "updated_at": "2015-07-10T06:13:29.693272Z",
            }
        ],
    )

    return [momconnect_prebirth_sub_id]


def mock_get_active_subscriptions_none(registrant_id, messageset=None):
    qs = "?active=True&identity={}".format(registrant_id)
    if messageset is not None:
        qs += "&messageset={}".format(messageset)
    mock_get_subscriptions(qs)

    return []


def mock_update_subscription(subscription_id, identity_id=None):
    responses.add(
        responses.PATCH,
        "http://sbm/api/v1/subscriptions/{}/".format(subscription_id),
        json={
            "id": subscription_id,
            "identity": identity_id,
            "active": True,
            "completed": False,
            "lang": "eng_ZA",
            "url": "http://sbm/api/v1/subscriptions/{}".format(subscription_id),
            "messageset": 32,
            "next_sequence_number": 32,
            "schedule": 132,
            "process_status": 0,
            "version": 1,
            "metadata": {},
            "created_at": "2015-07-10T06:13:29.693272Z",
            "updated_at": "2015-07-10T06:13:29.693272Z",
        },
        status=200,
        content_type="application/json",
    )


def mock_get_subscription(subscription_id, identity_id=None):
    responses.add(
        responses.GET,
        "http://sbm/api/v1/subscriptions/{}/".format(subscription_id),
        json={
            "id": subscription_id,
            "identity": identity_id,
            "active": True,
            "completed": False,
            "lang": "eng_ZA",
            "url": "http://sbm/api/v1/subscriptions/{}".format(subscription_id),
            "messageset": 32,
            "next_sequence_number": 32,
            "schedule": 132,
            "process_status": 0,
            "version": 1,
            "metadata": {},
            "created_at": "2015-07-10T06:13:29.693272Z",
            "updated_at": "2015-07-10T06:13:29.693272Z",
        },
        status=200,
        content_type="application/json",
    )


def mock_get_active_nurseconnect_subscriptions(registrant_id):
    nurseconnect_sub_id = "subscriptionid-nurseconnect-00000000"
    mock_get_subscriptions(
        "?active=True&messageset=61&identity={}".format(registrant_id),
        [
            {  # nurseconnect.hw_full.1 subscription
                "id": nurseconnect_sub_id,
                "identity": registrant_id,
                "active": True,
                "completed": False,
                "lang": "eng_ZA",
                "url": "http://sbm/api/v1/subscriptions/{}".format(nurseconnect_sub_id),
                "messageset": 61,
                "next_sequence_number": 11,
                "schedule": 161,
                "process_status": 0,
                "version": 1,
                "metadata": {},
                "created_at": "2015-07-10T06:13:29.693272Z",
                "updated_at": "2015-07-10T06:13:29.693272Z",
            }
        ],
    )

    return [nurseconnect_sub_id]


def mock_get_active_nurseconnect_childm_subscriptions(registrant_id):
    nurseconnect_sub_id = "subscriptionid-nurseconnect-00000000"
    mock_get_subscriptions(
        "?active=True&messageset=62&identity={}".format(registrant_id),
        [
            {  # nurseconnect.hw_full.1 subscription
                "id": nurseconnect_sub_id,
                "identity": registrant_id,
                "active": True,
                "completed": False,
                "lang": "eng_ZA",
                "url": "http://sbm/api/v1/subscriptions/{}".format(nurseconnect_sub_id),
                "messageset": 62,
                "next_sequence_number": 11,
                "schedule": 161,
                "process_status": 0,
                "version": 1,
                "metadata": {},
                "created_at": "2015-07-10T06:13:29.693272Z",
                "updated_at": "2015-07-10T06:13:29.693272Z",
            }
        ],
    )

    return [nurseconnect_sub_id]


def mock_deactivate_subscriptions(subscription_ids):
    for subscription_id in subscription_ids:
        responses.add(
            responses.PATCH,
            "http://sbm/api/v1/subscriptions/{}/".format(subscription_id),
            json={"active": False},
            status=200,
            content_type="application/json",
        )
    return


class APITestCase(TestCase):
    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()
        self.otherclient = APIClient()
        utils.get_today = override_get_today


class AuthenticatedAPITestCase(APITestCase):
    def _replace_post_save_hooks_change(self):
        def has_listeners():
            return post_save.has_listeners(Change)

        assert has_listeners(), (
            "Change model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )
        post_save.disconnect(receiver=psh_validate_implement, sender=Change)
        post_save.disconnect(receiver=model_saved, dispatch_uid="instance-saved-hook")
        assert not has_listeners(), (
            "Change model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )

    def _restore_post_save_hooks_change(self):
        def has_listeners():
            return post_save.has_listeners(Change)

        assert not has_listeners(), (
            "Change model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests."
        )
        post_save.connect(psh_validate_implement, sender=Change)

    def _replace_post_save_hooks_registration(self):
        def has_listeners():
            return post_save.has_listeners(Registration)

        assert has_listeners(), (
            "Registration model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )
        post_save.disconnect(
            receiver=psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )
        post_save.disconnect(
            receiver=psh_fire_created_metric,
            sender=Registration,
            dispatch_uid="psh_fire_created_metric",
        )
        post_save.disconnect(receiver=model_saved, dispatch_uid="instance-saved-hook")
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )

    def _restore_post_save_hooks_registration(self):
        def has_listeners():
            return post_save.has_listeners(Registration)

        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests."
        )
        post_save.connect(
            psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )
        post_save.connect(
            psh_fire_created_metric,
            sender=Registration,
            dispatch_uid="psh_fire_created_metric",
        )

    def make_source_adminuser(self):
        data = {
            "name": "test_source_adminuser",
            "authority": "hw_full",
            "user": User.objects.get(username="testadminuser"),
        }
        return Source.objects.create(**data)

    def make_source_normaluser(self):
        data = {
            "name": "test_source_normaluser",
            "authority": "patient",
            "user": User.objects.get(username="testnormaluser"),
        }
        return Source.objects.create(**data)

    def make_change_adminuser(self):
        data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"test_adminuser_change": "test_adminuser_changed"},
            "source": self.make_source_adminuser(),
        }
        return Change.objects.create(**data)

    def make_change_normaluser(self):
        data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"test_normaluser_change": "test_normaluser_changed"},
            "source": self.make_source_normaluser(),
        }
        return Change.objects.create(**data)

    def make_registration_pmtct_prebirth(self):
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-11-30",
            },
        }
        return Registration.objects.create(**registration_data)

    def make_registration_pmtct_postbirth(self):
        registration_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "baby_dob": "2016-01-01",
            },
        }
        return Registration.objects.create(**registration_data)

    def make_registration_nurseconnect(self, anonymised=False):
        if anonymised:
            data = {
                "operator_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
                "uuid_registrant": "nurse001-63e2-4acc-9b94-26663b9bc267",
                "uuid_device": "nurse001-63e2-4acc-9b94-26663b9bc267",
                "faccode": "123456",
            }
        else:
            data = {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821112222",
                "msisdn_device": "+27821112222",
                "faccode": "123456",
            }
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": data,
        }
        return Registration.objects.create(**registration_data)

    def make_registration_momconnect_prebirth(self):
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-11-30",
            },
        }
        return Registration.objects.create(**registration_data)

    def make_registration_whatsapp_pmtct_prebirth(self):
        registration_data = {
            "reg_type": "whatsapp_pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-11-30",
            },
        }
        return Registration.objects.create(**registration_data)

    def make_registration_whatsapp_prebirth(self):
        registration_data = {
            "reg_type": "whatsapp_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-11-30",
            },
        }
        return Registration.objects.create(**registration_data)

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self._replace_post_save_hooks_change()
        self._replace_post_save_hooks_registration()

        # Normal User setup
        self.normalusername = "testnormaluser"
        self.normalpassword = "testnormalpass"
        self.normaluser = User.objects.create_user(
            self.normalusername, "testnormaluser@example.com", self.normalpassword
        )
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken.key
        self.normalclient.credentials(HTTP_AUTHORIZATION="Token " + self.normaltoken)

        # Admin User setup
        self.adminusername = "testadminuser"
        self.adminpassword = "testadminpass"
        self.adminuser = User.objects.create_superuser(
            self.adminusername, "testadminuser@example.com", self.adminpassword
        )
        admintoken = Token.objects.create(user=self.adminuser)
        self.admintoken = admintoken.key
        self.adminclient.credentials(HTTP_AUTHORIZATION="Token " + self.admintoken)

    def tearDown(self):
        self._restore_post_save_hooks_change()
        self._restore_post_save_hooks_registration()


class TestChangeAPI(AuthenticatedAPITestCase):
    def test_get_change_adminuser(self):
        # Setup
        change = self.make_change_adminuser()
        # Execute
        response = self.adminclient.get(
            "/api/v1/change/{}/".format(change.id), content_type="application/json"
        )
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_change_normaluser(self):
        # Setup
        change = self.make_change_normaluser()
        # Execute
        response = self.normalclient.get(
            "/api/v1/change/{}/".format(change.id), content_type="application/json"
        )
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_change_adminuser(self):
        # Setup
        self.make_source_adminuser()
        post_data = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "action": "pmtct_loss_switch",
            "data": {"test_key1": "test_value1"},
        }
        # Execute
        response = self.adminclient.post(
            "/api/v1/change/", json.dumps(post_data), content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, "test_source_adminuser")
        self.assertEqual(d.action, "pmtct_loss_switch")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.adminuser)

    def test_create_change_normaluser(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "action": "pmtct_loss_switch",
            "data": {"test_key1": "test_value1"},
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/change/", json.dumps(post_data), content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, "test_source_normaluser")
        self.assertEqual(d.action, "pmtct_loss_switch")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.normaluser)

    def test_create_change_set_readonly_field(self):
        # Setup
        self.make_source_adminuser()
        post_data = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "action": "pmtct_loss_switch",
            "data": {"test_key1": "test_value1"},
            "validated": True,
        }
        # Execute
        response = self.adminclient.post(
            "/api/v1/change/", json.dumps(post_data), content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, "test_source_adminuser")
        self.assertEqual(d.action, "pmtct_loss_switch")
        self.assertEqual(d.validated, False)  # Should ignore True post_data
        self.assertEqual(d.data, {"test_key1": "test_value1"})

    def test_optout_inactive_identity(self):
        # Setup
        self.make_source_normaluser()
        post_data = {"data": {"identity_id": "846877e6-afaa-43de-acb1-09f61ad4de99"}}
        # Execute
        response = self.normalclient.post(
            "/api/v1/change/inactive/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, "test_source_normaluser")
        self.assertEqual(d.action, "momconnect_nonloss_optout")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"reason": "sms_failure"})


class TestChangeListAPI(AuthenticatedAPITestCase):
    def test_list_changes(self):
        # Setup
        change1 = self.make_change_adminuser()
        change2 = self.make_change_normaluser()
        change3 = self.make_change_normaluser()
        # Execute
        response = self.adminclient.get(
            "/api/v1/changes/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], str(change3.id))
        self.assertEqual(body["results"][1]["id"], str(change2.id))
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

        # Check pagination
        body = self.adminclient.get(body["next"]).json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["id"], str(change1.id))
        self.assertIsNotNone(body["previous"])
        self.assertIsNone(body["next"])

        body = self.adminclient.get(body["previous"]).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], str(change3.id))
        self.assertEqual(body["results"][1]["id"], str(change2.id))
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

    def test_list_changes_filtered(self):
        # Setup
        self.make_change_adminuser()
        change2 = self.make_change_normaluser()
        # Execute
        response = self.adminclient.get(
            "/api/v1/changes/?source={}".format(change2.source.id),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(change2.id))


class TestRegistrationCreation(AuthenticatedAPITestCase):
    def test_make_registration_pmtct_prebirth(self):
        # Setup
        # Execute
        self.make_registration_pmtct_prebirth()
        # Test
        d = Registration.objects.last()
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.data["mom_dob"], "1999-01-27")

    def test_make_registration_pmtct_postbirth(self):
        # Setup
        # Execute
        self.make_registration_pmtct_postbirth()
        # Test
        d = Registration.objects.last()
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.data["mom_dob"], "1999-01-27")

    def test_make_registration_nurseconnect(self):
        # Setup
        # Execute
        self.make_registration_nurseconnect()
        # Test
        d = Registration.objects.last()
        self.assertEqual(d.registrant_id, "nurse001-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.data["faccode"], "123456")

    def test_make_registration_momconnect_prebirth(self):
        # Setup
        # Execute
        self.make_registration_momconnect_prebirth()
        # Test
        d = Registration.objects.last()
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.data["mom_dob"], "1999-01-27")


class TestChangeValidation(AuthenticatedAPITestCase):
    def test_validate_baby_switch_good(self):
        """ Good data baby_switch test """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_baby_switch_malformed_data(self):
        """ Malformed data baby_switch test """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(change.data["invalid_fields"], ["Invalid UUID registrant_id"])

    def test_validate_pmtct_loss_optouts_good(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one good one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_pmtct_loss_optouts_malformed_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one malformed one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "pmtct_loss_switch",
            "data": {"reason": "not a reason we accept"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Not a valid loss reason"],
        )

    def test_validate_pmtct_loss_optouts_missing_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one missing one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(change.data["invalid_fields"], ["Optout reason is missing"])

    def test_validate_pmtct_nonloss_optouts_good(self):
        """ Good data nonloss optout """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_nonloss_optout",
            "data": {"reason": "not_hiv_pos"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_pmtct_nonloss_optouts_malformed_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one malformed one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "pmtct_nonloss_optout",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Not a valid nonloss reason"],
        )

    def test_validate_pmtct_nonloss_optouts_missing_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one missing one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(change.data["invalid_fields"], ["Optout reason is missing"])

    def test_validate_nurse_update_faccode_good(self):
        """ Good data faccode update """
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"faccode": "234567"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_nurse_update_faccode_and_sanc(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"faccode": "234567", "sanc_no": "1234"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Only one detail update can be submitted per Change"],
        )

    def test_validate_nurse_update_faccode_malformed(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001",
            "action": "nurse_update_detail",
            "data": {"faccode": ""},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Faccode invalid"],
        )

    # skip sanc_no and persal_no update tests - similar to faccode update

    def test_validate_nurse_update_sa_id_good(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {
                "id_type": "sa_id",
                "sa_id_no": "5101025009086",
                "dob": "1951-01-02",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_nurse_update_id_type_invalid(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"id_type": "dob", "dob": "1951-01-02"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"], ["ID type should be passport or sa_id"]
        )

    def test_validate_nurse_update_sa_id_field_wrong(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"id_type": "sa_id", "passport_no": "12345", "dob": "1951-01-02"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["SA ID update requires fields id_type, sa_id_no, dob"],
        )

    def test_validate_nurse_update_passport_good(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {
                "id_type": "passport",
                "passport_no": "12345",
                "passport_origin": "na",
                "dob": "1951-01-02",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_nurse_update_passport_field_missing(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {
                "id_type": "passport",
                "passport_no": "12345",
                "passport_origin": "na",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            [
                "Passport update requires fields id_type, passport_no, "
                "passport_origin, dob"
            ],
        )

    def test_validate_nurse_update_arbitrary(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"foo": "bar"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"], ["Could not parse detail update request"]
        )

    def test_validate_nurse_change_msisdn_good(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_change_msisdn",
            "data": {
                "msisdn_old": "+27820001001",
                "msisdn_new": "+27820001002",
                "msisdn_device": "+27820001001",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_nurse_change_msisdn_malformed(self):
        # Setup
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_change_msisdn",
            "data": {
                "msisdn_old": "+27820001001",
                "msisdn_new": "+27820001002",
                "msisdn_device": "+27820001003",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Device msisdn should be the same as new or old msisdn"],
        )

    def test_validate_nurse_optout_good(self):
        """ Good data nonloss optout """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_optout",
            "data": {"reason": "job_change"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_nurse_optout_malformed_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for pmtct, so just test one malformed one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "nurse_optout",
            "data": {"reason": "bored"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Not a valid optout reason"],
        )

    def test_validate_momconnect_loss_optouts_good(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for momconnect, so just test one good one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_momconnect_loss_optouts_malformed_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for momconnect, so just test one malformed one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "momconnect_loss_switch",
            "data": {"reason": "not a reason we accept"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Not a valid loss reason"],
        )

    def test_validate_momconnect_loss_optouts_missing_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for momconnect, so just test one missing one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(change.data["invalid_fields"], ["Optout reason is missing"])

    def test_validate_momconnect_nonloss_optouts_good(self):
        """ Good data nonloss optout """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_nonloss_optout",
            "data": {"reason": "unknown"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_validate_momconnect_nonloss_optouts_malformed_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for momconnect, so just test one malformed one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01",
            "action": "momconnect_nonloss_optout",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Invalid UUID registrant_id", "Not a valid nonloss reason"],
        )

    def test_validate_momconnect_nonloss_optouts_missing_data(self):
        """ Loss optout data blobs are essentially identical between different
        forms of loss optout for momconnect, so just test one missing one.
        """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, False)
        self.assertEqual(change.validated, False)
        self.assertEqual(change.data["invalid_fields"], ["Optout reason is missing"])

    def test_momconnect_change_language_missing_language(self):
        """
        If there is no language field when trying to change language,
        the validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_language",
            data={},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["language field is missing"])

    def test_momconnect_change_language_incorrect_language(self):
        """
        If the specified language is not a valid and recognised languaged, the
        validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_language",
            data={"language": "foo_bar"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["Not a valid language choice"])

    def test_momconnect_change_msisdn_missing_msisdn(self):
        """
        If the change request is missing the msisdn field, then the validation
        should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_msisdn",
            data={},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["msisdn field is missing"])

    def test_momconnect_change_msisdn_invalid_msisdn(self):
        """
        If an invalid msisdn is provided, then validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_msisdn",
            data={"msisdn": "foo"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["Not a valid MSISDN"])

    def test_momconnect_change_identification_id_type_missing(self):
        """
        If the id type is missing, validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["ID type missing"])

    def test_momconnect_change_identification_incorrect_id_type(self):
        """
        If the id type is not a valid choice, validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={"id_type": "foo"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"], ["ID type should be 'sa_id' or 'passport'"]
        )

    def test_momconnect_change_identification_id_number_missing(self):
        """
        If the id type is sa_id, but there's no ID number, validation should
        fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={"id_type": "sa_id"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["SA ID number missing"])

    def test_momconnect_change_identification_id_number_invalid(self):
        """
        If the id type is sa_id, but the ID number is not valid, validation
        should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={"id_type": "sa_id", "sa_id_no": "foo"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(change.data["invalid_fields"], ["SA ID number invalid"])

    def test_momconnect_change_identification_passport_details_missing(self):
        """
        If the id type is passport, but the passport details aren't given, the
        validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={"id_type": "passport"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Passport number missing", "Passport origin missing"],
        )

    def test_momconnect_change_identification_passport_details_invalid(self):
        """
        If the id type is passport, but the passport details are invalid, the
        validation should fail.
        """
        change = Change.objects.create(
            registrant_id="mother01-63e2-4acc-9b94-26663b9bc267",
            action="momconnect_change_identification",
            data={"id_type": "passport", "passport_no": "", "passport_origin": "foo"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"],
            ["Passport number invalid", "Passport origin invalid"],
        )

    def test_admin_change_subscription(self):
        """ Good data change messaging """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "admin_change_subscription",
            "data": {
                "messageset": "messageset_one",
                "subscription": "sub12312-63e2-4acc-9b94-26663b9bc267",
            },
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_admin_change_subscription_language(self):
        """ Good data change messaging """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "admin_change_subscription",
            "data": {
                "language": "eng_ZA",
                "subscription": "sub12312-63e2-4acc-9b94-26663b9bc267",
            },
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        # Execute
        c = validate_implement.validate(change)
        # Check
        change.refresh_from_db()
        self.assertEqual(c, True)
        self.assertEqual(change.validated, True)

    def test_admin_change_subscription_missing_fields(self):
        """ Missing data change messaging """
        # Setup
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "admin_change_subscription",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"],
            [
                "One of these fields must be populated: messageset, language",
                "Subscription field is missing",
            ],
        )

    def test_change_channel_missing_fields(self):
        """
        If a channel change request is missing the 'channel' field, it should
        be marked as invalid
        """
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "switch_channel",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"], ["'channel' is a required field"]
        )

    def test_change_channel_invalid_channel(self):
        """
        If a specified channel does not exist, the change should be marked as
        invalid.
        """
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "switch_channel",
            "data": {"channel": "foo"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)
        validate_implement(change.id)
        change.refresh_from_db()
        self.assertFalse(change.validated)
        self.assertEqual(
            change.data["invalid_fields"],
            ["'channel' must be one of ['sms', 'whatsapp']"],
        )


class TestChangeActions(AuthenticatedAPITestCase):
    @responses.activate
    def test_baby_switch_momconnect_pmtct_nurseconnect_subs(self):
        # Pretest
        self.assertEqual(Registration.objects.all().count(), 0)
        # Setup
        # make registrations
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscriptions request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messageset by id
        utils_tests.mock_get_messageset(11)
        utils_tests.mock_get_messageset(21)
        utils_tests.mock_get_messageset(32)
        utils_tests.mock_get_messageset(61)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-pmtct-prebirth-000000",
                "subscriptionid-momconnect-prebirth-0",
            ]
        )

        # . mock get pmtct_postbirth messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get momconnect_postrbirh messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_postbirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # . mock update mock_patch_identity
        # . this is a general patch - `responses` doesn't check the data
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 2)
        self.assertEqual(len(responses.calls), 13)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 11,
            },
        )

    @responses.activate
    def test_baby_switch_momconnect_only_sub(self):
        # Pretest
        self.assertEqual(Registration.objects.all().count(), 0)
        # Setup
        # make registrations
        self.make_registration_momconnect_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscriptions request
        mock_get_active_subs_mc(change_data["registrant_id"])

        # . mock get messageset by id
        utils_tests.mock_get_messageset(21)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(["subscriptionid-momconnect-prebirth-0"])

        # . mock get momconnect_postrbirh messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_postbirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # . mock update mock_patch_identity
        # . this is a general patch - `responses` doesn't check the data
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 8)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 11,
            },
        )

    @responses.activate
    def test_baby_switch_pmtct_whatsapp(self):
        """
        If the mother is subscribed to pmtct whatsapp, then when switching to
        baby messages, they should receive those through whatsapp as well.
        """
        # Pretest
        self.assertEqual(Registration.objects.all().count(), 0)
        # Setup
        # make registrations
        self.make_registration_whatsapp_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscriptions request
        sub = mock_get_active_subs_whatsapp(change_data["registrant_id"], [99])

        # . mock get messageset by id
        utils_tests.mock_get_messageset(99)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions([sub])

        # . mock get momconnect_postbirth messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_pmtct_postbirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # . mock update mock_patch_identity
        # . this is a general patch - `responses` doesn't check the data
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 8)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 11,
            },
        )

    @responses.activate
    def test_baby_switch_momconnect_whatsapp(self):
        """
        If the mother is subscribed to momconnect whatsapp, then when
        switching to baby messages, they should receive those through
        whatsapp as well.
        """
        # Pretest
        self.assertEqual(Registration.objects.all().count(), 0)
        # Setup
        # make registrations
        self.make_registration_whatsapp_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscriptions request
        sub = mock_get_active_subs_whatsapp(change_data["registrant_id"], [97])

        # . mock get messageset by id
        utils_tests.mock_get_messageset(97)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions([sub])

        # . mock get momconnect_postbirth messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_momconnect_postbirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # . mock update mock_patch_identity
        # . this is a general patch - `responses` doesn't check the data
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 8)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 11,
            },
        )

    @responses.activate
    def test_pmtct_loss_switch(self):
        # Setup
        # make registrations
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # . mock get messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "loss_miscarriage.patient.1"
        )

        # . mock get schedule
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 11)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 5,
            },
        )

    @responses.activate
    def test_pmtct_loss_switch_whatsapp(self):
        """
        If the mother was on the whatsapp message set, she should be switched
        to the whatsapp loss message set.
        """
        # Setup
        # make registrations
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        whatsapp_sub = mock_get_active_subs_whatsapp(change_data["registrant_id"], [98])

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions([whatsapp_sub])

        # . mock get messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_loss_miscarriage.patient.1"
        )

        # . mock get schedule
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 9)

        [sub_req] = SubscriptionRequest.objects.all()
        self.assertEqual(sub_req.messageset, 81)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 5,
            },
        )

    @responses.activate
    def test_pmtct_loss_optout(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_optout",
            "data": {"reason": "stillbirth"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # mock identity store lookup for jembi push
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 7)

        # Check jembi push
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/pmtctOptout"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "optoutreason": 2,
                "type": 10,
            },
        )

    @responses.activate
    def test_pmtct_loss_optout_management_command(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_optout",
            "data": {"reason": "stillbirth"},
            "source": self.make_source_normaluser(),
            "validated": True,
        }
        change = Change.objects.create(**change_data)

        # mock identity store lookup for jembi push
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        # Execute
        stdout = StringIO()
        call_command(
            "jembi_submit_optouts",
            "--since",
            format_timestamp(change.created_at - datetime.timedelta(seconds=1)),
            "--until",
            format_timestamp(change.created_at + datetime.timedelta(seconds=1)),
            stdout=stdout,
        )

        # Check jembi push
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/pmtctOptout"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "optoutreason": 2,
                "type": 10,
            },
        )

    @responses.activate
    def test_pmtct_nonloss_optout(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_nonloss_optout",
            "data": {"reason": "other"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messageset
        utils_tests.mock_get_messageset(11)
        utils_tests.mock_get_messageset(21)
        utils_tests.mock_get_messageset(32)
        utils_tests.mock_get_messageset(61)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(["subscriptionid-pmtct-prebirth-000000"])

        # mock identity store lookup for jembi push
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 8)

        # Check jembi push
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/pmtctOptout"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "optoutreason": 5,
                "type": 10,
            },
        )

    @responses.activate
    def test_nurse_update_detail(self):
        # Setup
        # make registration
        self.make_registration_nurseconnect()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_update_detail",
            "data": {"faccode": "234567"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_nurse_change_msisdn(self):
        # Setup
        # make registration
        self.make_registration_nurseconnect()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_change_msisdn",
            "data": {
                "msisdn_old": "+27821112222",
                "msisdn_new": "+27821113333",
                "msisdn_device": "+27821113333",
            },
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_nurse_optout(self):
        # Setup
        # make registration
        self.make_registration_nurseconnect()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_optout",
            "data": {"reason": "job_change"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)

        # mock get messagesets
        mock_get_all_messagesets()

        # . mock get nurseconnect subscription request
        mock_get_active_nurseconnect_subscriptions(change_data["registrant_id"])
        mock_get_active_subscriptions_none(change_data["registrant_id"], messageset=62)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(["subscriptionid-nurseconnect-00000000"])
        mock_get_messageset(61, "nurseconnect.hw_full.1")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 5)

        # Check Jembi send
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 8,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "rmsisdn": None,
                "faccode": "123456",
                "id": "27821112222^^^ZAF^TEL",
                "dob": None,
                "optoutreason": 7,
            },
        )

    @responses.activate
    def test_nurse_optout_reg_data_removed(self):
        # Setup
        # make registration
        self.make_registration_nurseconnect(True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_optout",
            "data": {"reason": "job_change"},
            "source": self.make_source_adminuser(),
        }
        change = Change.objects.create(**change_data)

        # mock get identity
        utils_tests.mock_get_identity_by_id(
            "nurse001-63e2-4acc-9b94-26663b9bc267",
            details={"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        # mock get messagesets
        mock_get_all_messagesets()

        # . mock get nurseconnect subscription request
        mock_get_active_nurseconnect_subscriptions(change_data["registrant_id"])
        mock_get_active_subscriptions_none(change_data["registrant_id"], messageset=62)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(["subscriptionid-nurseconnect-00000000"])
        mock_get_messageset(61, "nurseconnect.hw_full.1")

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 8)

        # Check Jembi send
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 8,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "rmsisdn": None,
                "faccode": "123456",
                "id": "27821112222^^^ZAF^TEL",
                "dob": None,
                "optoutreason": 7,
            },
        )

    @responses.activate
    def test_nurse_optout_through_management_command(self):
        # Setup
        # make registration
        self.make_registration_nurseconnect()
        self.assertEqual(Registration.objects.all().count(), 1)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "action": "nurse_optout",
            "data": {"reason": "job_change"},
            "source": self.make_source_adminuser(),
            "validated": True,
        }
        change = Change.objects.create(**change_data)

        utils_tests.mock_get_identity_by_id("nurse001-63e2-4acc-9b94-26663b9bc267")

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        # Execute
        stdout = StringIO()
        call_command(
            "jembi_submit_optouts",
            "--since",
            format_timestamp(change.created_at - datetime.timedelta(seconds=1)),
            "--until",
            format_timestamp(change.created_at + datetime.timedelta(seconds=1)),
            stdout=stdout,
        )

        # Check Jembi send
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "type": 8,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "rmsisdn": None,
                "faccode": "123456",
                "id": "27821112222^^^ZAF^TEL",
                "dob": None,
                "optoutreason": 7,
            },
        )

    @responses.activate
    def test_momconnect_loss_switch_has_active(self):
        # Setup
        # make registrations
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock get messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "loss_miscarriage.patient.1"
        )

        # . mock get schedule
        utils_tests.mock_get_schedule(schedule_id)

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 1)
        self.assertEqual(len(responses.calls), 11)
        subreq = SubscriptionRequest.objects.last()
        self.assertEqual(subreq.messageset, 51)
        self.assertEqual(subreq.schedule, 151)
        self.assertEqual(subreq.next_sequence_number, 1)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 5,
            },
        )

    @responses.activate
    def test_momconnect_loss_switch_no_active(self):
        # Setup
        # . make registrations
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # . make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {"reason": "miscarriage"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subscriptions_none(change_data["registrant_id"])

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_momconnect_babyloss_via_management_task(self):
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_switch",
            "data": {"reason": "stillbirth"},
            "source": self.make_source_normaluser(),
            "validated": True,
        }
        change = Change.objects.create(**change_data)

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        # Execute
        stdout = StringIO()
        call_command(
            "jembi_submit_babyloss",
            "--since",
            format_timestamp(change.created_at - datetime.timedelta(seconds=1)),
            "--until",
            format_timestamp(change.created_at + datetime.timedelta(seconds=1)),
            stdout=stdout,
        )

        # Check
        self.assertEqual(len(responses.calls), 3)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 5,
            },
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 changes.", str(change.pk), "Done."]),
        )

    @responses.activate
    def test_momconnect_babyswitch_via_management_task(self):
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser(),
            "validated": True,
        }
        change = Change.objects.create(**change_data)

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        # Execute
        stdout = StringIO()
        call_command(
            "jembi_submit_babyswitch",
            "--since",
            format_timestamp(change.created_at - datetime.timedelta(seconds=1)),
            "--until",
            format_timestamp(change.created_at + datetime.timedelta(seconds=1)),
            stdout=stdout,
        )

        # Check
        self.assertEqual(len(responses.calls), 3)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 11,
            },
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 changes.", str(change.pk), "Done."]),
        )

    @responses.activate
    def test_momconnect_loss_optout(self):
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_optout",
            "data": {"reason": "stillbirth"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get all messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 7)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 4,
                "optoutreason": 2,
            },
        )

    @responses.activate
    def test_momconnect_loss_optout_via_management_task(self):
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_loss_optout",
            "data": {"reason": "stillbirth"},
            "source": self.make_source_normaluser(),
            "validated": True,
        }
        change = Change.objects.create(**change_data)

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        # Execute
        stdout = StringIO()
        call_command(
            "jembi_submit_optouts",
            "--since",
            format_timestamp(change.created_at - datetime.timedelta(seconds=1)),
            "--until",
            format_timestamp(change.created_at + datetime.timedelta(seconds=1)),
            stdout=stdout,
        )

        # Check
        self.assertEqual(len(responses.calls), 3)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 4,
                "optoutreason": 2,
            },
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 changes.", str(change.pk), "Done."]),
        )

    @responses.activate
    def test_momconnect_nonloss_optout(self):
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_nonloss_optout",
            "data": {"reason": "other"},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 7)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27111111111",
                "dmsisdn": "+27111111111",
                "type": 4,
                "optoutreason": 5,
            },
        )

    @responses.activate
    def test_momconnect_nonloss_optout_with_identity_optout(self):
        """
        If there is a identity optout in the change payload it should be sent
        to the identity store.
        """
        # Setup
        # make registration
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "momconnect_nonloss_optout",
            "data": {
                "reason": "other",
                "identity_store_optout": {
                    "optout_type": "forget",
                    "identity": "mother01-63e2-4acc-9b94-26663b9bc267",
                    "reason": "unknown",
                    "address_type": "msisdn",
                    "address": "",
                    "request_source": "ussd_popi_user_data",
                },
            },
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        mock_get_active_subs_mcpre_mcpost_pmtct_nc(change_data["registrant_id"])

        # . mock get messagesets
        mock_get_all_messagesets()

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(
            [
                "subscriptionid-momconnect-prebirth-0",
                "subscriptionid-momconnect-postbirth-",
                "subscriptionid-pmtct-prebirth-000000",
            ]
        )

        # mock identity lookup
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27111111111": {}}}},
        )

        # mock post to jembi
        responses.add(
            responses.POST,
            "http://jembi/ws/rest/v1/optout",
            json={"foo": "bar"},
            status=200,
            content_type="application/json",
        )

        # mock identity store post
        responses.add(
            responses.POST,
            "http://is/api/v1/optout/",
            json={"foo": "bar"},
            status=200,
            content_type="application/json",
        )

        # Execute
        result = validate_implement.apply_async(args=[change.id])

        # Check
        change.refresh_from_db()
        self.assertEqual(result.get(), True)
        self.assertEqual(change.validated, True)
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        self.assertEqual(len(responses.calls), 8)

        # Check Identity Store optout POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "address": "",
                "address_type": "msisdn",
                "identity": "mother01-63e2-4acc-9b94-26663b9bc267",
                "optout_type": "forget",
                "reason": "unknown",
                "request_source": "ussd_popi_user_data",
            },
        )

    @responses.activate
    def test_momconnect_change_language_identity(self):
        """
        The language change should change the language on the lang_code field
        on the identity.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id, {"lang_code": "eng_ZA", "foo": "bar"}
        )
        utils_tests.mock_patch_identity(registrant_id)

        mock_get_active_subscriptions_none(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_language",
            data={"language": "xho_ZA"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        _, get_identity, patch_identity = responses.calls
        self.assertIn(registrant_id, get_identity.request.url)
        self.assertEqual(
            json.loads(get_identity.response.text)["details"],
            {"lang_code": "eng_ZA", "foo": "bar"},
        )
        self.assertEqual(
            json.loads(patch_identity.request.body),
            {"details": {"lang_code": "xho_ZA", "foo": "bar"}},
        )

    @responses.activate
    def test_momconnect_change_language_subscriptions(self):
        """
        The language change should change the language of all of the momconnect
        subscriptions.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(registrant_id)

        [_, prebirth, _, postbirth] = mock_get_active_subs_mcpre_mcpost_pmtct_nc(
            registrant_id
        )
        mock_update_subscription(prebirth)
        mock_update_subscription(postbirth)
        mock_get_messageset(11, "pmtct_prebirth.patient.1")
        mock_get_messageset(21, "momconnect_prebirth.hw_full.1")
        mock_get_messageset(61, "nurseconnect.hw_full.1")
        mock_get_messageset(32, "momconnect_postbirth.hw_full.1")
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_language",
            data={"language": "xho_ZA"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        (
            _,
            ms_11,
            ms_21,
            prebirth_update,
            ms_61,
            ms_32,
            postbirth_update,
            _,
            _,
        ) = responses.calls
        self.assertNotIn("momconnect", ms_11.response.text)
        self.assertIn("momconnect", ms_21.response.text)
        self.assertEqual(json.loads(prebirth_update.request.body), {"lang": "xho_ZA"})
        self.assertNotIn("momconnect", ms_61.response.text)
        self.assertIn("momconnect", ms_32.response.text)
        self.assertEqual(json.loads(postbirth_update.request.body), {"lang": "xho_ZA"})

    @responses.activate
    def test_momconnect_change_language_old_language(self):
        """
        The action should update the change data with the previous language
        that was set on the identity before the change.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id, {"lang_code": "eng_ZA", "foo": "bar"}
        )
        utils_tests.mock_patch_identity(registrant_id)

        mock_get_active_subscriptions_none(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_language",
            data={"language": "xho_ZA"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertEqual(change.data["language"], "xho_ZA")
        self.assertEqual(change.data["old_language"], "eng_ZA")

    @responses.activate
    def test_momconnect_change_msisdn_new_msisdn(self):
        """
        if the new msisdn doesn't exist in the contacts existing msisdns, then
        all existing msisdns should be marked as not default, and the new
        msisdn should be added and made default.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id,
            details={
                "addresses": {
                    "msisdn": {"+27123456789": {"default": True}, "+27123456788": {}}
                }
            },
        )
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_msisdn",
            data={"msisdn": "+27987654321"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "addresses": {
                        "msisdn": {
                            "+27123456789": {
                                "default": False,
                                "changes_from": [str(change.id)],
                            },
                            "+27123456788": {},
                            "+27987654321": {
                                "default": True,
                                "changes_to": [str(change.id)],
                            },
                        }
                    },
                }
            },
        )

    @responses.activate
    def test_momconnect_change_msisdn_no_addresses(self):
        """
        If the addresses field, or any of the nested field are missing from
        the identity, they should be added, along with the details of the
        new address.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(registrant_id, details={})
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_msisdn",
            data={"msisdn": "+27987654321"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "addresses": {
                        "msisdn": {
                            "+27987654321": {
                                "default": True,
                                "changes_to": [str(change.id)],
                            }
                        }
                    },
                }
            },
        )

    @responses.activate
    def test_momconnect_change_msisdn_existing_msisdn(self):
        """
        If the new msisdn already exists on the identity, then all other
        msisdns should be marked as not default, and the new msisdn marked
        as default.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id,
            details={
                "addresses": {
                    "msisdn": {"+27123456789": {"default": True}, "+27987654321": {}}
                }
            },
        )
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_msisdn",
            data={"msisdn": "+27987654321"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "addresses": {
                        "msisdn": {
                            "+27987654321": {
                                "default": True,
                                "changes_to": [str(change.id)],
                            },
                            "+27123456789": {
                                "default": False,
                                "changes_from": [str(change.id)],
                            },
                        }
                    },
                }
            },
        )

    @responses.activate
    def test_momconnect_change_msisdn_existing_changes(self):
        """
        If there are previous changes to this identity, we should append the
        change ID to the list of existing changes.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id,
            details={
                "addresses": {
                    "msisdn": {
                        "+27123456789": {
                            "default": True,
                            "changes_from": ["test-change-id1"],
                        },
                        "+27987654321": {"changes_to": ["test-change-id2"]},
                    }
                }
            },
        )
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_msisdn",
            data={"msisdn": "+27987654321"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "addresses": {
                        "msisdn": {
                            "+27987654321": {
                                "default": True,
                                "changes_to": ["test-change-id2", str(change.id)],
                            },
                            "+27123456789": {
                                "default": False,
                                "changes_from": ["test-change-id1", str(change.id)],
                            },
                        }
                    },
                }
            },
        )

    @responses.activate
    def test_momconnect_change_msisdn_no_existing_defaults(self):
        """
        If there are no existing defaults for an identity, then the change_from
        field should be set on all msisdn addresses.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id,
            details={
                "addresses": {
                    "msisdn": {
                        "+27123456789": {"changes_from": ["test-change-id1"]},
                        "+27123456788": {},
                    }
                }
            },
        )
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_msisdn",
            data={"msisdn": "+27987654321"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "addresses": {
                        "msisdn": {
                            "+27987654321": {
                                "default": True,
                                "changes_to": [str(change.id)],
                            },
                            "+27123456789": {
                                "changes_from": ["test-change-id1", str(change.id)]
                            },
                            "+27123456788": {"changes_from": [str(change.id)]},
                        }
                    },
                }
            },
        )

    @responses.activate
    def test_momconnect_change_identification_sa_id(self):
        """
        If the new type of identification is of type sa_id, it should update
        the sa_id_no field and place the old identification data in the
        identification history.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            registrant_id, {"passport_no": "1234", "passport_origin": "other"}
        )
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_identification",
            data={"id_type": "sa_id", "sa_id_no": "1234567890123"},
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "sa_id_no": "1234567890123",
                    "identification_history": [
                        {
                            "change": str(change.id),
                            "passport_no": "1234",
                            "passport_origin": "other",
                        }
                    ],
                }
            },
        )

    @responses.activate
    def test_momconnect_change_identification_passport(self):
        """
        If the new type of identification is of type passport, it should update
        the passport_no and passport_origin fields and place the old
        identification data in the identification history.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(registrant_id, {"sa_id_no": "1234"})
        utils_tests.mock_patch_identity(registrant_id)

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="momconnect_change_identification",
            data={
                "id_type": "passport",
                "passport_no": "1234567890123",
                "passport_origin": "other",
            },
            source=self.make_source_normaluser(),
        )
        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)
        self.assertEqual(change.data, {})
        [_, identity_update] = responses.calls
        self.assertEqual(
            json.loads(identity_update.request.body),
            {
                "details": {
                    "lang_code": "afr_ZA",
                    "foo": "bar",
                    "passport_no": "1234567890123",
                    "passport_origin": "other",
                    "identification_history": [
                        {"change": str(change.id), "sa_id_no": "1234"}
                    ],
                }
            },
        )

    @responses.activate
    def test_admin_change_subscription_messageset(self):
        """
        Change messaging should disable the specified subscription and create a
        new subscription request with the new messageset
        """

        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        subscription_id = "sub12312-63e2-4acc-9b94-26663b9bc267"
        messageset_name = "momconnect_prebirth.hw_full.1"

        mock_get_subscription(subscription_id, registrant_id)
        mock_deactivate_subscriptions([subscription_id])
        mock_search_messageset(32, messageset_name)

        change_data = {
            "registrant_id": registrant_id,
            "action": "admin_change_subscription",
            "data": {"messageset": messageset_name, "subscription": subscription_id},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)

        s = SubscriptionRequest.objects.last()
        self.assertEqual(s.identity, registrant_id)
        self.assertEqual(s.messageset, 32)

    @responses.activate
    def test_admin_change_subscription_language(self):
        """
        Change language only should update the existing subscription language
        """

        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        subscription_id = "sub12312-63e2-4acc-9b94-26663b9bc267"
        language = "zul_ZA"

        mock_update_subscription(subscription_id, registrant_id)

        change_data = {
            "registrant_id": registrant_id,
            "action": "admin_change_subscription",
            "data": {"subscription": subscription_id, "language": language},
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)

        s = SubscriptionRequest.objects.count()
        self.assertEqual(s, 0)

    @responses.activate
    def test_admin_change_subscription_both(self):
        """
        Change messaging should disable the specified subscription and create a
        new subscription request with the new messageset and language
        """

        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        subscription_id = "sub12312-63e2-4acc-9b94-26663b9bc267"
        messageset_name = "momconnect_prebirth.hw_full.1"
        language = "zul_ZA"

        mock_get_subscription(subscription_id, registrant_id)
        mock_deactivate_subscriptions([subscription_id])
        mock_search_messageset(32, messageset_name)

        change_data = {
            "registrant_id": registrant_id,
            "action": "admin_change_subscription",
            "data": {
                "messageset": messageset_name,
                "subscription": subscription_id,
                "language": language,
            },
            "source": self.make_source_normaluser(),
        }
        change = Change.objects.create(**change_data)

        validate_implement(change.id)
        change.refresh_from_db()

        self.assertTrue(change.validated)

        s = SubscriptionRequest.objects.last()
        self.assertEqual(s.identity, registrant_id)
        self.assertEqual(s.messageset, 32)
        self.assertEqual(s.lang, language)

    @responses.activate
    def test_switch_channel_skips_non_active(self):
        """
        Switching the channel should skip all inactive subscriptions.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets([])
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id), [{"active": False}]
        )

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "sms"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)

        # Check Jembi POST
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "type": 12,
                "channel_current": "whatsapp",
                "channel_new": change.data["channel"],
            },
        )

    @responses.activate
    def test_switch_channel_to_sms_skips_service_info(self):
        """
        Switching the channel to SMS should skip service info subscriptions.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets(["whatsapp_service_info.hw_full.1", "momconnect_prebirth"])
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id),
            [
                {
                    "id": "sub1",
                    "messageset": 0,
                    "identity": registrant_id,
                    "next_sequence_number": 7,
                    "lang": "eng",
                    "schedule": 2,
                    "active": True,
                },
                {"messageset": 1, "active": True},
            ],
        )
        mock_deactivate_subscriptions(["sub1"])

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "sms"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertTrue(change.data["old_channel"], "whatsapp")

        self.assertEqual(SubscriptionRequest.objects.count(), 0)

        # Check Jembi POST
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/messageChange"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "type": 12,
                "channel_current": "whatsapp",
                "channel_new": change.data["channel"],
            },
        )

    @responses.activate
    def test_switch_channel_to_sms(self):
        """
        Switching to SMS should change all other subscriptions to SMS
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets(["whatsapp_momconnect_prebirth", "momconnect_prebirth"])
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id),
            [
                {
                    "id": "sub1",
                    "messageset": 0,
                    "identity": registrant_id,
                    "next_sequence_number": 7,
                    "lang": "eng",
                    "schedule": 2,
                    "active": True,
                },
                {"messageset": 1, "active": True},
            ],
        )
        mock_deactivate_subscriptions(["sub1"])

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "sms"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertTrue(change.data["old_channel"], "whatsapp")

        [sub_req] = SubscriptionRequest.objects.all()
        self.assertEqual(sub_req.identity, registrant_id)
        self.assertEqual(sub_req.messageset, 1)
        self.assertEqual(sub_req.next_sequence_number, 7)
        self.assertEqual(sub_req.lang, "eng")
        self.assertEqual(sub_req.schedule, 2)

        # Check Jembi POST
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/messageChange"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "type": 12,
                "channel_current": "whatsapp",
                "channel_new": change.data["channel"],
            },
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_switch_channel_to_sms_not_available(self, mock_create_outbound):
        """
        Switching to SMS where there is no corrosponding WHatsapp set should
        not change the subscription to sms and should send a notification to
        the user.
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets(
            ["whatsapp_momconnect_prebirth", "not_momconnect_prebirth"]
        )
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id),
            [
                {
                    "id": "sub1",
                    "messageset": 0,
                    "identity": registrant_id,
                    "next_sequence_number": 7,
                    "lang": "eng",
                    "schedule": 2,
                    "active": True,
                },
                {"messageset": 1, "active": True},
            ],
        )

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "sms"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertTrue(change.data["error"], "No whatsapp available")

        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "mother01-63e2-4acc-9b94-26663b9bc267",
                "content": (
                    "We notice that you have been receiving MomConnect msgs on "
                    "WhatsApp for children between 1 - 2. Messages for children "
                    "between 1 - 2 are only available on WhatsApp - switching to "
                    "SMS means you will not receive any messages. You can stop "
                    "your MomConnect messages completely by replying ‘STOP‘"
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @responses.activate
    def test_switch_channel_to_whatsapp(self):
        """
        Switching to WhatsApp should change all other subscriptions to WhatsApp
        and create a service_info subscription
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets(
            [
                "whatsapp_momconnect_prebirth",
                "momconnect_prebirth",
                "whatsapp_service_info",
            ]
        )
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id),
            [
                {
                    "id": "sub1",
                    "messageset": 1,
                    "identity": registrant_id,
                    "next_sequence_number": 7,
                    "lang": "eng",
                    "schedule": 2,
                    "active": True,
                },
                {"messageset": 0, "active": True},
            ],
        )
        mock_deactivate_subscriptions(["sub1"])

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        reg = self.make_registration_momconnect_prebirth()
        reg.source = self.make_source_adminuser()
        reg.save()

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "whatsapp"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertTrue(change.data["old_channel"], "sms")

        [sub_req, sub_service_info] = SubscriptionRequest.objects.all()
        self.assertEqual(sub_req.identity, registrant_id)
        self.assertEqual(sub_req.messageset, 0)
        self.assertEqual(sub_req.next_sequence_number, 7)
        self.assertEqual(sub_req.lang, "eng")
        self.assertEqual(sub_req.schedule, 2)

        self.assertEqual(sub_service_info.identity, registrant_id)
        self.assertEqual(sub_service_info.messageset, 0)
        self.assertEqual(sub_service_info.next_sequence_number, 1)
        self.assertEqual(sub_service_info.lang, "eng")
        self.assertEqual(sub_service_info.schedule, 1)

        # Check Jembi POST
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/messageChange"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "type": 12,
                "channel_current": "sms",
                "channel_new": change.data["channel"],
            },
        )

    @responses.activate
    def test_switch_channel_to_whatsapp_skip_service_info(self):
        """
        Switching to WhatsApp should change all other subscriptions to WhatsApp
        and not create a service_info subscription if it's a public subscription
        """
        registrant_id = "mother01-63e2-4acc-9b94-26663b9bc267"
        mock_get_messagesets(
            [
                "whatsapp_momconnect_prebirth",
                "momconnect_prebirth",
                "whatsapp_service_info",
            ]
        )
        mock_get_subscriptions(
            "?identity={}&active=True".format(registrant_id),
            [
                {
                    "id": "sub1",
                    "messageset": 1,
                    "identity": registrant_id,
                    "next_sequence_number": 7,
                    "lang": "eng",
                    "schedule": 2,
                    "active": True,
                },
                {"messageset": 0, "active": True},
            ],
        )
        mock_deactivate_subscriptions(["sub1"])

        # . mock get identity by id
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            {"addresses": {"msisdn": {"+27821112222": {}}}},
        )

        self.make_registration_momconnect_prebirth()

        change = Change.objects.create(
            registrant_id=registrant_id,
            action="switch_channel",
            data={"channel": "whatsapp"},
            source=self.make_source_normaluser(),
        )

        validate_implement(change.id)
        change.refresh_from_db()
        self.assertTrue(change.validated)
        self.assertTrue(change.data["old_channel"], "sms")

        [sub_req] = SubscriptionRequest.objects.all()
        self.assertEqual(sub_req.identity, registrant_id)
        self.assertEqual(sub_req.messageset, 0)
        self.assertEqual(sub_req.next_sequence_number, 7)
        self.assertEqual(sub_req.lang, "eng")
        self.assertEqual(sub_req.schedule, 2)

        # Check Jembi POST
        self.assertEqual(
            responses.calls[-1].request.url, "http://jembi/ws/rest/v1/messageChange"
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "encdate": change.created_at.strftime("%Y%m%d%H%M%S"),
                "mha": 1,
                "swt": 1,
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "type": 12,
                "channel_current": "sms",
                "channel_new": change.data["channel"],
            },
        )


class TestRemovePersonallyIdentifiableInformation(AuthenticatedAPITestCase):
    @responses.activate
    def test_removes_personal_information_fields(self):
        """
        For each of the personal information fields, the task should remove
        them from the Change object, and instead place them on the identity
        that the Change is for.
        """
        change = Change.objects.create(
            registrant_id="mother-uuid",
            action="baby_switch",
            source=self.make_source_normaluser(),
            validated=True,
            data={
                "id_type": "passport",
                "dob": "1990-01-01",
                "passport_no": "12345",
                "passport_origin": "na",
                "sa_id_no": "4321",
                "persal_no": "111",
                "sanc_no": "222",
                "foo": "baz",
            },
        )

        utils_tests.mock_get_identity_by_id("mother-uuid")
        utils_tests.mock_patch_identity("mother-uuid")

        remove_personally_identifiable_fields(str(change.pk))

        identity_update = json.loads(responses.calls[-1].request.body)
        self.assertEqual(
            identity_update["details"],
            {
                "id_type": "passport",
                "dob": "1990-01-01",
                "passport_no": "12345",
                "passport_origin": "na",
                "sa_id_no": "4321",
                "persal_no": "111",
                "sanc_no": "222",
                "lang_code": "afr_ZA",
                "foo": "bar",
            },
        )

        change.refresh_from_db()
        self.assertEqual(change.data, {"foo": "baz"})

    @responses.activate
    def test_changes_msisdns_to_uuids(self):
        """
        For each of the msisdn fields, the task should remove them from the
        Change object, and put back the UUID field instead.
        """
        change = Change.objects.create(
            registrant_id="mother-uuid",
            action="baby_switch",
            source=self.make_source_normaluser(),
            validated=True,
            data={
                "msisdn_device": "+27111",
                "msisdn_new": "+27222",
                "msisdn_old": "+27333",
                "msisdn_foo": "+27444",
            },
        )

        utils_tests.mock_get_identity_by_msisdn("+27111", "device-uuid")
        utils_tests.mock_get_identity_by_msisdn("+27222", "new-uuid")
        utils_tests.mock_get_identity_by_msisdn("+27333", "old-uuid")

        remove_personally_identifiable_fields(str(change.pk))

        change.refresh_from_db()
        self.assertEqual(
            change.data,
            {
                "uuid_device": "device-uuid",
                "uuid_new": "new-uuid",
                "uuid_old": "old-uuid",
                "msisdn_foo": "+27444",
            },
        )

    @responses.activate
    def test_creates_missing_identities(self):
        """
        For each of the msisdn fields, if the identity doesn't exist, then
        it should be created.
        """
        change = Change.objects.create(
            registrant_id="mother-uuid",
            action="baby_switch",
            source=self.make_source_normaluser(),
            validated=True,
            data={"msisdn_device": "+27111"},
        )

        utils_tests.mock_get_identity_by_msisdn("+27111", num=0)
        utils_tests.mock_create_identity("device-uuid")

        remove_personally_identifiable_fields(str(change.pk))

        identity_creation = json.loads(responses.calls[-1].request.body)
        self.assertEqual(
            identity_creation["details"], {"addresses": {"msisdn": {"+27111": {}}}}
        )

        change.refresh_from_db()
        self.assertEqual(change.data, {"uuid_device": "device-uuid"})


class TestRestorePersonallyIdentifiableInformation(AuthenticatedAPITestCase):
    @responses.activate
    def test_restores_personal_information_fields(self):
        """
        Any personal information fields that exist on the identity, but
        not on the change object, should be placed on the change object.
        """
        change = Change.objects.create(
            registrant_id="mother-uuid",
            action="baby_switch",
            source=self.make_source_normaluser(),
            validated=True,
            data={"id_type": "passport"},
        )

        utils_tests.mock_get_identity_by_id(
            "mother-uuid",
            {
                "id_type": "sa_id",
                "dob": "1990-01-01",
                "passport_no": "1234",
                "passport_origin": "na",
                "sa_id_no": "4321",
                "persal_no": "111",
                "sanc_no": "222",
            },
        )

        restore_personally_identifiable_fields(change)
        self.assertEqual(
            change.data,
            {
                "id_type": "passport",
                "dob": "1990-01-01",
                "passport_no": "1234",
                "passport_origin": "na",
                "sa_id_no": "4321",
                "persal_no": "111",
                "sanc_no": "222",
            },
        )

    @responses.activate
    def test_restores_msisdn_fields(self):
        """
        If any of the uuid fields exist on the change object, then an msisdn
        lookup should be done for those msisdns, and the msisdn should be
        placed on the change object.
        """
        change = Change.objects.create(
            registrant_id="mother-uuid",
            action="baby_switch",
            source=self.make_source_normaluser(),
            validated=True,
            data={
                "uuid_device": "device-uuid",
                "uuid_new": "new-uuid",
                "uuid_old": "old-uuid",
            },
        )

        utils_tests.mock_get_identity_by_id("mother-uuid")
        utils_tests.mock_get_identity_by_id(
            "device-uuid", {"addresses": {"msisdn": {"+1111": {}}}}
        )
        utils_tests.mock_get_identity_by_id(
            "new-uuid",
            {"addresses": {"msisdn": {"+2222": {"default": True}, "+3333": {}}}},
        )
        utils_tests.mock_get_identity_by_id("old-uuid")

        restore_personally_identifiable_fields(change)
        self.assertEqual(
            change.data,
            {
                "uuid_device": "device-uuid",
                "uuid_new": "new-uuid",
                "uuid_old": "old-uuid",
                "msisdn_device": "+1111",
                "msisdn_new": "+2222",
            },
        )


class ControlInterfaceOptoutViewTest(AuthenticatedAPITestCase):

    """
    Tests related to the optout control interface view.
    """

    def test_ci_optout_invalid(self):
        request = {}

        response = self.adminclient.post(
            "/api/v1/optout_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            utils.json_decode(response.content),
            {"registrant_id": ["This field is required."]},
        )
        self.assertEqual(len(responses.calls), 0)

    @responses.activate
    def test_ci_optout(self):
        identity = "846877e6-afaa-43de-acb1-09f61ad4de99"
        request = {"registrant_id": identity}

        mock_get_active_subs_mcpre_mcpost_pmtct_nc(identity)
        mock_get_messageset(11, "pmtct_prebirth.patient.1")
        mock_get_messageset(21, "momconnect_prebirth.hw_full.1")
        mock_get_messageset(61, "nurseconnect.hw_full.1")
        mock_get_messageset(32, "momconnect_postbirth.hw_full.1")

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/optout_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(utils.json_decode(response.content)), 3)

        changes = Change.objects.filter(registrant_id=identity)
        self.assertEqual(changes.count(), 3)
        changes = Change.objects.filter(
            registrant_id=identity, action="momconnect_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(
            registrant_id=identity, action="pmtct_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(registrant_id=identity, action="nurse_optout")
        self.assertEqual(changes.count(), 1)
        self.assertEqual(changes[0].source.name, "test_source_adminuser")

    @responses.activate
    def test_ci_optout_no_source_username(self):
        identity = "846877e6-afaa-43de-acb1-09f61ad4de99"
        request = {"registrant_id": identity}

        mock_get_active_subs_mcpre_mcpost_pmtct_nc(identity)
        mock_get_messageset(11, "pmtct_prebirth.patient.1")
        mock_get_messageset(21, "momconnect_prebirth.hw_full.1")
        mock_get_messageset(61, "nurseconnect.hw_full.1")
        mock_get_messageset(32, "momconnect_postbirth.hw_full.1")

        user = User.objects.get(username="testnormaluser")

        response = self.normalclient.post(
            "/api/v1/optout_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(utils.json_decode(response.content)), 3)

        changes = Change.objects.filter(registrant_id=identity)
        self.assertEqual(changes.count(), 3)
        changes = Change.objects.filter(
            registrant_id=identity, action="momconnect_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(
            registrant_id=identity, action="pmtct_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(registrant_id=identity, action="nurse_optout")
        self.assertEqual(changes.count(), 1)

        source = Source.objects.last()
        self.assertEqual(source.name, user.username)
        self.assertEqual(source.user, user)
        self.assertEqual(source.authority, "advisor")

    @responses.activate
    def test_ci_optout_no_source(self):
        identity = "846877e6-afaa-43de-acb1-09f61ad4de99"
        request = {"registrant_id": identity}

        mock_get_active_subs_mcpre_mcpost_pmtct_nc(identity)
        mock_get_messageset(11, "pmtct_prebirth.patient.1")
        mock_get_messageset(21, "momconnect_prebirth.hw_full.1")
        mock_get_messageset(61, "nurseconnect.hw_full.1")
        mock_get_messageset(32, "momconnect_postbirth.hw_full.1")

        user = User.objects.get(username="testnormaluser")
        user.first_name = "John"
        user.last_name = "Doe"
        user.save()

        response = self.normalclient.post(
            "/api/v1/optout_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(utils.json_decode(response.content)), 3)

        changes = Change.objects.filter(registrant_id=identity)
        self.assertEqual(changes.count(), 3)
        changes = Change.objects.filter(
            registrant_id=identity, action="momconnect_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(
            registrant_id=identity, action="pmtct_nonloss_optout"
        )
        self.assertEqual(changes.count(), 1)
        changes = Change.objects.filter(registrant_id=identity, action="nurse_optout")
        self.assertEqual(changes.count(), 1)

        source = Source.objects.last()
        self.assertEqual(source.name, user.get_full_name())
        self.assertEqual(source.user, user)
        self.assertEqual(source.authority, "advisor")

    def test_ci_change_no_identity(self):
        request = {}

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/change_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            utils.json_decode(response.content),
            {
                "registrant_id": ["This field is required."],
                "subscription": ["This field is required."],
            },
        )
        self.assertEqual(len(responses.calls), 0)

    def test_ci_change_invalid(self):
        request = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "subscription": "846877e6-afaa-43de-acb1-111111111111",
        }

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/change_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            utils.json_decode(response.content),
            {
                "non_field_errors": [
                    "One of these fields must be populated: messageset, language"
                ]
            },
        )  # noqa

    def test_ci_change_language(self):
        request = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "subscription": "846877e6-afaa-43de-acb1-111111111111",
            "language": "eng_ZA",
        }

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/change_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        change = Change.objects.last()
        self.assertEqual(change.registrant_id, "846877e6-afaa-43de-acb1-09f61ad4de99")
        self.assertEqual(change.action, "admin_change_subscription")
        self.assertEqual(
            change.data,
            {
                "language": "eng_ZA",
                "subscription": "846877e6-afaa-43de-acb1-111111111111",
            },
        )

    def test_ci_change_messaging(self):
        request = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "subscription": "846877e6-afaa-43de-acb1-111111111111",
            "messageset": "messageset_one",
        }

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/change_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        change = Change.objects.last()
        self.assertEqual(change.registrant_id, "846877e6-afaa-43de-acb1-09f61ad4de99")
        self.assertEqual(change.action, "admin_change_subscription")
        self.assertEqual(
            change.data,
            {
                "messageset": "messageset_one",
                "subscription": "846877e6-afaa-43de-acb1-111111111111",
            },
        )

    def test_ci_change_language_and_messaging(self):
        identity = "846877e6-afaa-43de-acb1-09f61ad4de99"
        subscription = "846877e6-afaa-43de-acb1-111111111111"
        request = {
            "registrant_id": identity,
            "subscription": subscription,
            "messageset": "messageset_one",
            "language": "eng_ZA",
        }

        self.make_source_adminuser()
        response = self.adminclient.post(
            "/api/v1/change_admin/",
            json.dumps(request),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        changes = Change.objects.filter(registrant_id=identity)
        self.assertEqual(changes.count(), 1)
        self.assertEqual(changes[0].action, "admin_change_subscription")
        self.assertEqual(
            changes[0].data,
            {
                "messageset": "messageset_one",
                "subscription": subscription,
                "language": "eng_ZA",
            },
        )
