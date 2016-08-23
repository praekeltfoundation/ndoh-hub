import datetime
import json
import responses

from django.test import TestCase
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_hooks.models import model_saved

from ndoh_hub import utils, utils_tests
from registrations.models import (Source, Registration,
                                  psh_validate_subscribe)
from .models import Change, psh_implement_action
from .tasks import implement_action


def override_get_today():
    return datetime.datetime.strptime("20150817", "%Y%m%d")


def mock_get_active_subscriptions(registrant_id):
    subscription_id_1 = "subscription1-4bf1-8779-c47b428e89d0"
    subscription_id_2 = "subscription2-4bf1-8779-c47b428e89d0"
    responses.add(
        responses.GET,
        'http://sbm/api/v1/subscriptions/?active=True&id=%s' % registrant_id,
        json={
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {   # pmtct_prebirth.patient.1 subscription
                    "id": subscription_id_1,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/%s" % (
                        subscription_id_1),
                    "messageset": 11,
                    "next_sequence_number": 11,
                    "schedule": 101,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z"
                },
                {   # momconnect_prebirth.hw_full.1 subscription
                    "id": subscription_id_2,
                    "identity": registrant_id,
                    "active": True,
                    "completed": False,
                    "lang": "eng_ZA",
                    "url": "http://sbm/api/v1/subscriptions/%s" % (
                        subscription_id_2),
                    "messageset": 21,
                    "next_sequence_number": 21,
                    "schedule": 121,
                    "process_status": 0,
                    "version": 1,
                    "metadata": {},
                    "created_at": "2015-07-10T06:13:29.693272Z",
                    "updated_at": "2015-07-10T06:13:29.693272Z"
                }
            ],
        },
        status=200, content_type='application/json',
        match_querystring=True
    )

    return [subscription_id_1, subscription_id_2]


def mock_deactivate_subscriptions(subscription_ids):
    for subscription_id in subscription_ids:
        responses.add(
            responses.PATCH,
            'http://sbm/api/v1/subscriptions/%s/' % subscription_id,
            json={"active": False},
            status=200, content_type='application/json',
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
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(receiver=psh_implement_action,
                             sender=Change)
        post_save.disconnect(receiver=model_saved,
                             dispatch_uid='instance-saved-hook')
        assert not has_listeners(), (
            "Change model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks_change(self):
        def has_listeners():
            return post_save.has_listeners(Change)
        assert not has_listeners(), (
            "Change model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(psh_implement_action, sender=Change)

    def _replace_post_save_hooks_registration(self):
        def has_listeners():
            return post_save.has_listeners(Registration)
        assert has_listeners(), (
            "Registration model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(receiver=psh_validate_subscribe,
                             sender=Registration)
        post_save.disconnect(receiver=model_saved,
                             dispatch_uid='instance-saved-hook')
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks_registration(self):
        def has_listeners():
            return post_save.has_listeners(Registration)
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(psh_validate_subscribe, sender=Registration)

    def make_source_adminuser(self):
        data = {
            "name": "test_source_adminuser",
            "authority": "hw_full",
            "user": User.objects.get(username='testadminuser')
        }
        return Source.objects.create(**data)

    def make_source_normaluser(self):
        data = {
            "name": "test_source_normaluser",
            "authority": "patient",
            "user": User.objects.get(username='testnormaluser')
        }
        return Source.objects.create(**data)

    def make_change_adminuser(self):
        data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"test_adminuser_change": "test_adminuser_changed"},
            "source": self.make_source_adminuser()
        }
        return Change.objects.create(**data)

    def make_change_normaluser(self):
        data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {"test_normaluser_change": "test_normaluser_changed"},
            "source": self.make_source_normaluser()
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
                "baby_dob": "2016-01-01"
            },
        }
        return Registration.objects.create(**registration_data)

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self._replace_post_save_hooks_change()
        self._replace_post_save_hooks_registration()

        # Normal User setup
        self.normalusername = 'testnormaluser'
        self.normalpassword = 'testnormalpass'
        self.normaluser = User.objects.create_user(
            self.normalusername,
            'testnormaluser@example.com',
            self.normalpassword)
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken.key
        self.normalclient.credentials(
            HTTP_AUTHORIZATION='Token ' + self.normaltoken)

        # Admin User setup
        self.adminusername = 'testadminuser'
        self.adminpassword = 'testadminpass'
        self.adminuser = User.objects.create_superuser(
            self.adminusername,
            'testadminuser@example.com',
            self.adminpassword)
        admintoken = Token.objects.create(user=self.adminuser)
        self.admintoken = admintoken.key
        self.adminclient.credentials(
            HTTP_AUTHORIZATION='Token ' + self.admintoken)

    def tearDown(self):
        self._restore_post_save_hooks_change()
        self._restore_post_save_hooks_registration()


class TestChangeAPI(AuthenticatedAPITestCase):

    def test_get_change_adminuser(self):
        # Setup
        change = self.make_change_adminuser()
        # Execute
        response = self.adminclient.get(
            '/api/v1/change/%s/' % change.id,
            content_type='application/json')
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_change_normaluser(self):
        # Setup
        change = self.make_change_normaluser()
        # Execute
        response = self.normalclient.get(
            '/api/v1/change/%s/' % change.id,
            content_type='application/json')
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_change_adminuser(self):
        # Setup
        self.make_source_adminuser()
        post_data = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "action": "pmtct_loss_switch",
            "data": {"test_key1": "test_value1"}
        }
        # Execute
        response = self.adminclient.post('/api/v1/change/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, 'test_source_adminuser')
        self.assertEqual(d.action, 'pmtct_loss_switch')
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.adminuser)

    def test_create_change_normaluser(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "registrant_id": "846877e6-afaa-43de-acb1-09f61ad4de99",
            "action": "pmtct_loss_switch",
            "data": {"test_key1": "test_value1"}
        }
        # Execute
        response = self.normalclient.post('/api/v1/change/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, 'test_source_normaluser')
        self.assertEqual(d.action, 'pmtct_loss_switch')
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
            "validated": True
        }
        # Execute
        response = self.adminclient.post('/api/v1/change/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Change.objects.last()
        self.assertEqual(d.source.name, 'test_source_adminuser')
        self.assertEqual(d.action, 'pmtct_loss_switch')
        self.assertEqual(d.validated, False)  # Should ignore True post_data
        self.assertEqual(d.data, {"test_key1": "test_value1"})


class TestRegistrationCreation(AuthenticatedAPITestCase):

    def test_make_registration_pmtct_prebirth(self):
        # Setup
        # Execute
        self.make_registration_pmtct_prebirth()
        # Test
        d = Registration.objects.last()
        self.assertEqual(d.registrant_id,
                         "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.data["mom_dob"], "1999-01-27")


class TestChangeActions(AuthenticatedAPITestCase):

    @responses.activate
    def test_baby_switch_with_active_pmtct_subscription(self):
        # Pretest
        self.assertEqual(Registration.objects.all().count(), 0)
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "baby_switch",
            "data": {},
            "source": self.make_source_normaluser()
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        active_subscription_ids = mock_get_active_subscriptions(
            change_data["registrant_id"])

        # . mock get messageset by id
        utils_tests.mock_get_messageset(11)
        utils_tests.mock_get_messageset(21)

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(active_subscription_ids)

        # . mock get messageset by shortname
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        result = implement_action.apply_async(args=[change.id])

        # Check
        self.assertEqual(result.get(), "Switch to baby completed")
        self.assertEqual(Registration.objects.all().count(), 1)

    @responses.activate
    def test_pmtct_loss_switch(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_switch",
            "data": {
                "reason": "miscarriage"
            },
            "source": self.make_source_normaluser()
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        active_subscription_ids = mock_get_active_subscriptions(
            change_data["registrant_id"])

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(active_subscription_ids)

        # Execute
        result = implement_action.apply_async(args=[change.id])

        # Check
        self.assertEqual(result.get(), "PMTCT switch to loss completed")

    @responses.activate
    def test_pmtct_loss_optout(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_loss_optout",
            "data": {
                "reason": "stillbirth"
            },
            "source": self.make_source_normaluser()
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        active_subscription_ids = mock_get_active_subscriptions(
            change_data["registrant_id"])

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(active_subscription_ids)

        # Execute
        result = implement_action.apply_async(args=[change.id])

        # Check
        self.assertEqual(result.get(), "PMTCT optout due to loss completed")

    @responses.activate
    def test_pmtct_nonloss_optout(self):
        # Setup
        # make registration
        self.make_registration_pmtct_prebirth()
        # make change object
        change_data = {
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "action": "pmtct_nonloss_optout",
            "data": {
                "reason": "other"
            },
            "source": self.make_source_normaluser()
        }
        change = Change.objects.create(**change_data)

        # . mock get subscription request
        active_subscription_ids = mock_get_active_subscriptions(
            change_data["registrant_id"])

        # . mock deactivate active subscriptions
        mock_deactivate_subscriptions(active_subscription_ids)

        # Execute
        result = implement_action.apply_async(args=[change.id])

        # Check
        self.assertEqual(result.get(),
                         "PMTCT optout not due to loss completed")
