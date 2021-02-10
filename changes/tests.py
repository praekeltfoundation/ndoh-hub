import datetime
import json

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
from registrations.signals import psh_validate_subscribe

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


class TestChangeActions(AuthenticatedAPITestCase):
    @responses.activate
    def test_momconnect_babyloss_via_management_task(self):
        # Setup
        # make registration
        jembi_url = "http://jembi/ws/rest/v1/subscription"
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "id": "106be577-5963-491b-ac5d-7f4f0f4da309",
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

        utils_tests.mock_request_to_jembi_api(jembi_url)

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
                "sid": change.registrant_id,
                "eid": "106be577-5963-491b-ac5d-7f4f0f4da309",
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
        jembi_url = "http://jembi/ws/rest/v1/subscription"
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "id": "106be577-5963-491b-ac5d-7f4f0f4da309",
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

        utils_tests.mock_request_to_jembi_api(jembi_url)

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
                "sid": change.registrant_id,
                "eid": "106be577-5963-491b-ac5d-7f4f0f4da309",
                "type": 11,
            },
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 changes.", str(change.pk), "Done."]),
        )

    @responses.activate
    def test_momconnect_loss_optout_via_management_task(self):
        # Setup
        # make registration
        jembi_url = "http://jembi/ws/rest/v1/optout"
        self.make_registration_momconnect_prebirth()
        self.make_registration_pmtct_prebirth()
        self.assertEqual(Registration.objects.all().count(), 2)
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)
        # make change object
        change_data = {
            "id": "106be577-5963-491b-ac5d-7f4f0f4da309",
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

        utils_tests.mock_request_to_jembi_api(jembi_url)

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
                "sid": change.registrant_id,
                "eid": "106be577-5963-491b-ac5d-7f4f0f4da309",
                "type": 4,
                "optoutreason": 2,
            },
        )
        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 changes.", str(change.pk), "Done."]),
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
