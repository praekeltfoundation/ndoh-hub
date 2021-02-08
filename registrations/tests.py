import json
import datetime
import uuid
from unittest import mock
from uuid import UUID

import responses
from django.contrib.auth.models import Group, User
from django.core import management
from django.core.cache import cache
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_hooks.models import model_saved

from ndoh_hub import utils, utils_tests

from .models import JembiSubmission, Registration, Source, SubscriptionRequest
from .signals import psh_validate_subscribe
from .tasks import (
    PushRegistrationToJembi,
    add_personally_identifiable_fields,
    push_nurse_registration_to_jembi,
    remove_personally_identifiable_fields,
    validate_subscribe,
)

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def override_get_today():
    return datetime.datetime.strptime("2016-01-01", "%Y-%m-%d").date()


class TestUtils(TestCase):
    def test_is_valid_date(self):
        # Setup
        good_date = "1982-03-15"
        invalid_date = "1983-02-29"
        bad_date = "1234"
        # Execute
        # Check
        self.assertEqual(utils.is_valid_date(good_date), True)
        self.assertEqual(utils.is_valid_date(invalid_date), False)
        self.assertEqual(utils.is_valid_date(bad_date), False)

    def test_is_valid_edd(self):
        # Setup
        good_edd = "2016-03-01"
        past_edd = "2015-12-31"
        far_future_edd = "2017-01-01"
        not_date = "1234"
        # Execute
        # Check
        with mock.patch("ndoh_hub.utils.get_today", override_get_today):
            self.assertEqual(utils.is_valid_edd(good_edd), True)
            self.assertEqual(utils.is_valid_edd(past_edd), False)
            self.assertEqual(utils.is_valid_edd(far_future_edd), False)
            self.assertEqual(utils.is_valid_edd(not_date), False)

    def test_is_valid_uuid(self):
        # Setup
        valid_uuid = str(uuid.uuid4())
        invalid_uuid = "f9bfa2d7-5b62-4011-8eac-76bca34781a"
        # Execute
        # Check
        self.assertEqual(utils.is_valid_uuid(valid_uuid), True)
        self.assertEqual(utils.is_valid_uuid(invalid_uuid), False)

    def test_is_valid_lang(self):
        # Setup
        valid_lang = "eng_ZA"
        invalid_lang = "south african"
        # Execute
        # Check
        self.assertEqual(utils.is_valid_lang(valid_lang), True)
        self.assertEqual(utils.is_valid_lang(invalid_lang), False)

    def test_is_valid_msisdn(self):
        self.assertEqual(utils.is_valid_msisdn("+27821112222"), True)
        self.assertEqual(utils.is_valid_msisdn("+2782111222"), False)
        self.assertEqual(utils.is_valid_msisdn("0821112222"), False)

    def test_get_mom_age(self):
        t = override_get_today()

        self.assertEqual(utils.get_mom_age(t, "1998-01-01"), 18)
        self.assertEqual(utils.get_mom_age(t, "1998-01-02"), 17)


class APITestCase(TestCase):
    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()
        self.partialclient = APIClient()
        self.otherclient = APIClient()
        utils.get_today = override_get_today


class AuthenticatedAPITestCase(APITestCase):
    def _replace_post_save_hooks(self):
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

    def _restore_post_save_hooks(self):
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

    def make_source_partialuser(self):
        data = {
            "name": "test_source_partialuser",
            "authority": "hw_partial",
            "user": User.objects.get(username="testpartialuser"),
        }
        return Source.objects.create(**data)

    def make_source_normaluser(self, name="test_source_normaluser"):
        data = {
            "name": name,
            "authority": "patient",
            "user": User.objects.get(username="testnormaluser"),
        }
        return Source.objects.create(**data)

    def make_external_source_partial(self):
        data = {
            "name": "test_source_external_partial",
            "authority": "hw_partial",
            "user": User.objects.get(username="testpartialuser"),
        }
        return Source.objects.create(**data)

    def make_external_source_full(self):
        data = {
            "name": "test_source_external_full",
            "authority": "hw_full",
            "user": User.objects.get(username="testadminuser"),
        }
        return Source.objects.create(**data)

    def make_registration_adminuser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_adminuser_reg_key": "test_adminuser_reg_value"},
            "source": self.make_source_adminuser(),
        }
        return Registration.objects.create(**data)

    def make_registration_normaluser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_normaluser_reg_key": "test_normaluser_reg_value"},
            "source": self.make_source_normaluser(),
        }
        return Registration.objects.create(**data)

    def make_different_registrations(self):
        registration1_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-11-30",
            },
            "validated": True,
        }
        registration1 = Registration.objects.create(**registration1_data)
        registration2_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother02-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "baby_dob": "2016-01-01",
            },
            "validated": False,
        }
        registration2 = Registration.objects.create(**registration2_data)

        return (registration1, registration2)

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self._replace_post_save_hooks()

        # Normal User setup
        self.normalusername = "testnormaluser"
        self.normalpassword = "testnormalpass"
        self.normaluser = User.objects.create_user(
            self.normalusername, "testnormaluser@example.com", self.normalpassword
        )
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken
        self.normalclient.credentials(HTTP_AUTHORIZATION="Token %s" % self.normaltoken)

        # Admin User setup
        self.adminusername = "testadminuser"
        self.adminpassword = "testadminpass"
        self.adminuser = User.objects.create_superuser(
            self.adminusername, "testadminuser@example.com", self.adminpassword
        )
        admintoken = Token.objects.create(user=self.adminuser)
        self.admintoken = admintoken
        self.adminclient.credentials(HTTP_AUTHORIZATION="Token %s" % self.admintoken)

        # Partial User setup
        self.partialusername = "testpartialuser"
        self.partialpassword = "testpartialpass"
        self.partialuser = User.objects.create_user(
            self.partialusername, "testpartialuser@example.com", self.partialpassword
        )
        partialtoken = Token.objects.create(user=self.partialuser)
        self.partialtoken = partialtoken
        self.partialclient.credentials(
            HTTP_AUTHORIZATION="Token %s" % self.partialtoken
        )

        patcher = mock.patch("registrations.tasks.opt_in_identity")
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("registrations.tasks.send_welcome_message")
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self._restore_post_save_hooks()


class TestLogin(AuthenticatedAPITestCase):
    def test_login_normaluser(self):
        """ Test that normaluser can login successfully
        """
        # Setup
        post_auth = {"username": "testnormaluser", "password": "testnormalpass"}
        # Execute
        request = self.client.post("/api/token-auth/", post_auth)
        token = request.data.get("token", None)
        # Check
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post."
        )
        self.assertEqual(
            request.status_code,
            200,
            "Status code on /api/token-auth was %s (should be 200)."
            % request.status_code,
        )

    def test_login_adminuser(self):
        """ Test that adminuser can login successfully
        """
        # Setup
        post_auth = {"username": "testadminuser", "password": "testadminpass"}
        # Execute
        request = self.client.post("/api/token-auth/", post_auth)
        token = request.data.get("token", None)
        # Check
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post."
        )
        self.assertEqual(
            request.status_code,
            200,
            "Status code on /api/token-auth was %s (should be 200)."
            % request.status_code,
        )

    def test_login_adminuser_wrong_password(self):
        """ Test that adminuser cannot log in with wrong password
        """
        # Setup
        post_auth = {"username": "testadminuser", "password": "wrongpass"}
        # Execute
        request = self.client.post("/api/token-auth/", post_auth)
        token = request.data.get("token", None)
        # Check
        self.assertIsNone(
            token, "Could not receive authentication token on login post."
        )
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_otheruser(self):
        """ Test that an unknown user cannot log in
        """
        # Setup
        post_auth = {"username": "testotheruser", "password": "testotherpass"}
        # Execute
        request = self.otherclient.post("/api/token-auth/", post_auth)
        token = request.data.get("token", None)
        # Check
        self.assertIsNone(
            token, "Could not receive authentication token on login post."
        )
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)


class TestUserCreation(AuthenticatedAPITestCase):
    def test_create_user_and_token(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.adminclient.post("/api/v1/user/token/", user_request)
        token = request.json().get("token", None)
        # Check
        self.assertIsNotNone(token, "Could not receive authentication token on post.")
        self.assertEqual(
            request.status_code,
            201,
            "Status code on /api/v1/user/token/ was %s (should be 201)."
            % request.status_code,
        )

    def test_create_user_and_token_fail_nonadmin(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.normalclient.post("/api/v1/user/token/", user_request)
        error = request.json().get("detail", None)
        # Check
        self.assertIsNotNone(error, "Could not receive error on post.")
        self.assertEqual(
            error,
            "You do not have permission to perform this action.",
            "Error message was unexpected: %s." % error,
        )

    def test_create_user_and_token_not_created(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.adminclient.post("/api/v1/user/token/", user_request)
        token = request.json().get("token", None)
        # And again, to get the same token
        request2 = self.adminclient.post("/api/v1/user/token/", user_request)
        token2 = request2.json().get("token", None)

        # Check
        self.assertEqual(
            token, token2, "Tokens are not equal, should be the same as not recreated."
        )

    def test_create_user_new_token_nonadmin(self):
        # Setup
        user_request = {"email": "test@example.org"}
        request = self.adminclient.post("/api/v1/user/token/", user_request)
        token = request.json().get("token", None)
        cleanclient = APIClient()
        cleanclient.credentials(HTTP_AUTHORIZATION="Token %s" % token)
        # Execute
        request = cleanclient.post("/api/v1/user/token/", user_request)
        error = request.json().get("detail", None)
        # Check
        # new user should not be admin
        self.assertIsNotNone(error, "Could not receive error on post.")
        self.assertEqual(
            error,
            "You do not have permission to perform this action.",
            "Error message was unexpected: %s." % error,
        )

    def test_list_users(self):
        # Execute
        response = self.adminclient.get(
            "/api/v1/user/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["username"], self.normaluser.username)
        self.assertEqual(body["results"][1]["username"], self.adminuser.username)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

        # Check pagination
        body = self.adminclient.get(body["next"]).json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["username"], self.partialuser.username)
        self.assertIsNotNone(body["previous"])
        self.assertIsNone(body["next"])

        body = self.adminclient.get(body["previous"]).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["username"], self.normaluser.username)
        self.assertEqual(body["results"][1]["username"], self.adminuser.username)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

    def test_list_groups(self):
        groups = []
        for i in range(1, 4):
            groups.append(Group.objects.create(name="group_%s" % i))
        # Execute
        response = self.adminclient.get(
            "/api/v1/group/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["name"], groups[0].name)
        self.assertEqual(body["results"][1]["name"], groups[1].name)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

        # Check pagination
        body = self.adminclient.get(body["next"]).json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["name"], groups[2].name)
        self.assertIsNotNone(body["previous"])
        self.assertIsNone(body["next"])

        body = self.adminclient.get(body["previous"]).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["name"], groups[0].name)
        self.assertEqual(body["results"][1]["name"], groups[1].name)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])


class TestSourceAPI(AuthenticatedAPITestCase):
    def test_get_source_adminuser(self):
        # Setup
        source = self.make_source_adminuser()
        # Execute
        response = self.adminclient.get(
            "/api/v1/source/%s/" % source.id,
            format="json",
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authority"], "hw_full")
        self.assertEqual(response.data["name"], "test_source_adminuser")

    def test_get_source_normaluser(self):
        # Setup
        source = self.make_source_normaluser()
        # Execute
        response = self.normalclient.get(
            "/api/v1/source/%s/" % source.id, content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_source_adminuser(self):
        # Setup
        user = User.objects.get(username="testadminuser")
        post_data = {
            "name": "test_source_name",
            "authority": "patient",
            "user": "/api/v1/user/%s/" % user.id,
        }
        # Execute
        response = self.adminclient.post(
            "/api/v1/source/", json.dumps(post_data), content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        d = Source.objects.last()
        self.assertEqual(d.name, "test_source_name")
        self.assertEqual(d.authority, "patient")

    def test_create_source_normaluser(self):
        # Setup
        user = User.objects.get(username="testnormaluser")
        post_data = {
            "name": "test_source_name",
            "authority": "hw_full",
            "user": "/api/v1/user/%s/" % user.id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/source/", json.dumps(post_data), content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_source(self):
        source1 = self.make_source_adminuser()
        source2 = self.make_source_normaluser()
        source3 = self.make_source_normaluser()

        # Execute
        response = self.adminclient.get(
            "/api/v1/source/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], source1.id)
        self.assertEqual(body["results"][1]["id"], source2.id)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

        # Check pagination
        body = self.adminclient.get(body["next"]).json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["id"], source3.id)
        self.assertIsNotNone(body["previous"])
        self.assertIsNone(body["next"])

        body = self.adminclient.get(body["previous"]).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], source1.id)
        self.assertEqual(body["results"][1]["id"], source2.id)
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])


class TestRegistrationAPI(AuthenticatedAPITestCase):
    def test_get_registration_adminuser(self):
        # Setup
        registration = self.make_registration_adminuser()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registration/%s/" % registration.id,
            content_type="application/json",
        )
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_registration_normaluser(self):
        # Setup
        registration = self.make_registration_normaluser()
        # Execute
        response = self.normalclient.get(
            "/api/v1/registration/%s/" % registration.id,
            content_type="application/json",
        )
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_registration_adminuser(self):
        # Setup
        self.make_source_adminuser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_key1": "test_value1"},
        }
        # Execute
        response = self.adminclient.post(
            "/api/v1/registration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_adminuser")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.adminuser)

    def test_create_registration_normaluser(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_key1": "test_value1"},
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/registration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_normaluser")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.normaluser)

    def test_create_registration_set_readonly_field(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_key1": "test_value1"},
            "validated": True,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/registration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_normaluser")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.validated, False)  # Should ignore True post_data
        self.assertEqual(d.data, {"test_key1": "test_value1"})

    def test_list_registrations(self):
        # Setup
        registration1 = self.make_registration_normaluser()
        registration2 = self.make_registration_adminuser()
        registration3 = self.make_registration_normaluser()
        # Execute
        response = self.normalclient.get(
            "/api/v1/registrations/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], str(registration3.id))
        self.assertEqual(body["results"][1]["id"], str(registration2.id))
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

        # Check pagination
        body = self.normalclient.get(body["next"]).json()
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["id"], str(registration1.id))
        self.assertIsNotNone(body["previous"])
        self.assertIsNone(body["next"])

        body = self.normalclient.get(body["previous"]).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["id"], str(registration3.id))
        self.assertEqual(body["results"][1]["id"], str(registration2.id))
        self.assertIsNone(body["previous"])
        self.assertIsNotNone(body["next"])

    def test_filter_registration_registrant_id(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?registrant_id=%s" % (registration1.registrant_id),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_reg_type(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?reg_type=%s" % registration2.reg_type,
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_validated(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?validated=%s" % registration1.validated,
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_source(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?source=%s" % registration2.source.id,
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_created_after(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # While the '+00:00' is valid according to ISO 8601, the version of
        # django-filter we are using does not support it
        date_string = registration2.created_at.isoformat().replace("+00:00", "Z")
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?created_after=%s" % date_string,
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_created_before(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # While the '+00:00' is valid according to ISO 8601, the version of
        # django-filter we are using does not support it
        date_string = registration1.created_at.isoformat().replace("+00:00", "Z")
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?created_before=%s" % date_string,
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_no_matches(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?registrant_id=test_id",
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_registration_unknown_filter(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            "/api/v1/registrations/?something=test_id", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)


@override_settings(
    IDENTITY_STORE_URL="http://identitystore/",
    IDENTITY_STORE_TOKEN="identitystore_token",
)
class TestThirdPartyRegistrationAPI(AuthenticatedAPITestCase):
    @mock.patch("ndoh_hub.utils.get_today")
    @responses.activate
    def test_create_third_party_registration_existing_identity(self, today):
        today.return_value = datetime.date(2016, 11, 1)
        # Setup
        self.make_external_source_partial()

        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27831111111",  # noqa
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "created_at": "2015-10-14T07:25:53.218988Z",
                        "created_by": 53,
                        "details": {
                            "addresses": {
                                "msisdn": {"+27831111111": {"default": True}}
                            },
                            "default_addr_type": "msisdn",
                        },
                        "id": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                        "operator": None,
                        "updated_at": "2016-10-27T19:04:03.138598Z",
                        "updated_by": 53,
                        "version": 1,
                    }
                ],
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27824440000",  # noqa
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "communicate_through": None,
                        "created_at": "2015-10-14T07:25:53.218988Z",
                        "created_by": 53,
                        "details": {
                            "addresses": {
                                "msisdn": {"+27824440000": {"default": True}}
                            },
                            "consent": False,
                            "default_addr_type": "msisdn",
                            "lang_code": "eng_ZA",
                            "last_mc_reg_on": "clinic",
                            "mom_dob": "1999-02-21",
                            "sa_id_no": "27625249986",
                            "source": "clinic",
                        },
                        "id": "02144938-847d-4d2c-9daf-707cb864d077",
                        "operator": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                        "updated_at": "2016-10-27T19:04:03.138598Z",
                        "updated_by": 53,
                        "version": 1,
                    }
                ],
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.PATCH,
            "http://identitystore/identities/02144938-847d-4d2c-9daf-707cb864d077/",  # noqa
            json={
                "communicate_through": None,
                "created_at": "2015-10-14T07:25:53.218988Z",
                "created_by": 53,
                "details": {
                    "addresses": {"msisdn": {"+27824440000": {"default": True}}},
                    "consent": False,
                    "default_addr_type": "msisdn",
                    "lang_code": "eng_ZA",
                    "last_mc_reg_on": "clinic",
                    "mom_dob": "1999-02-21",
                    "sa_id_no": "27625249986",
                    "source": "clinic",
                },
                "id": "02144938-847d-4d2c-9daf-707cb864d077",
                "operator": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                "updated_at": "2016-10-27T19:04:03.138598Z",
                "updated_by": 53,
                "version": 1,
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        post_data = {
            "hcw_msisdn": "+27831111111",
            "mom_msisdn": "+27824440000",
            "mom_id_type": "none",
            "mom_passport_origin": None,
            "mom_id_no": "27625249986",
            "mom_lang": "en",
            "mom_edd": "2016-11-05",
            "mom_dob": "1999-02-21",
            "clinic_code": None,
            "authority": "chw",
            "consent": True,
            "mha": 2,
            "swt": 3,
            "encdate": "20160101000001",
        }
        # Execute
        response = self.partialclient.post(
            "/api/v1/extregistration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_external_partial")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "02144938-847d-4d2c-9daf-707cb864d077")
        self.assertEqual(d.data["edd"], "2016-11-05")
        self.assertEqual(d.data["encdate"], "20160101000001")

    @mock.patch("ndoh_hub.utils.get_today")
    @responses.activate
    def test_create_third_party_registration_new_identity(self, today):
        today.return_value = datetime.date(2016, 11, 1)
        # Setup
        self.make_external_source_partial()

        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27831111111",  # noqa
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "created_at": "2015-10-14T07:25:53.218988Z",
                        "created_by": 53,
                        "details": {
                            "addresses": {
                                "msisdn": {"+27831111111": {"default": True}}
                            },
                            "default_addr_type": "msisdn",
                        },
                        "id": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                        "operator": None,
                        "updated_at": "2016-10-27T19:04:03.138598Z",
                        "updated_by": 53,
                        "version": 1,
                    }
                ],
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27824440000",  # noqa
            json={"next": None, "previous": None, "results": []},
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.POST,
            "http://identitystore/identities/",
            json={
                "communicate_through": None,
                "created_at": "2015-10-14T07:25:53.218988Z",
                "created_by": 53,
                "details": {
                    "addresses": {"msisdn": {"+27824440000": {"default": True}}},
                    "consent": False,
                    "default_addr_type": "msisdn",
                    "lang_code": "eng_ZA",
                    "last_mc_reg_on": "clinic",
                    "mom_dob": "1999-02-21",
                    "sa_id_no": "27625249986",
                    "source": "clinic",
                },
                "id": "02144938-847d-4d2c-9daf-707cb864d077",
                "operator": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                "updated_at": "2016-10-27T19:04:03.138598Z",
                "updated_by": 53,
                "version": 1,
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        post_data = {
            "hcw_msisdn": "+27831111111",
            "mom_msisdn": "+27824440000",
            "mom_id_type": "none",
            "mom_passport_origin": None,
            "mom_id_no": "27625249986",
            "mom_lang": "en",
            "mom_edd": "2016-11-05",
            "mom_dob": "1999-02-21",
            "clinic_code": None,
            "authority": "chw",
            "consent": True,
            "mha": 2,
            "swt": 3,
        }
        # Execute
        response = self.partialclient.post(
            "/api/v1/extregistration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_external_partial")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "02144938-847d-4d2c-9daf-707cb864d077")
        self.assertEqual(d.data["edd"], "2016-11-05")

    @mock.patch("ndoh_hub.utils.get_today")
    @responses.activate
    def test_create_third_party_registration_no_swt_mha(self, today):
        today.return_value = datetime.date(2016, 11, 1)
        # Setup
        self.make_external_source_partial()

        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27831111111",  # noqa
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "created_at": "2015-10-14T07:25:53.218988Z",
                        "created_by": 53,
                        "details": {
                            "addresses": {
                                "msisdn": {"+27831111111": {"default": True}}
                            },
                            "default_addr_type": "msisdn",
                        },
                        "id": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                        "operator": None,
                        "updated_at": "2016-10-27T19:04:03.138598Z",
                        "updated_by": 53,
                        "version": 1,
                    }
                ],
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.GET,
            "http://identitystore/identities/search/?details__addresses__msisdn=%2B27824440000",  # noqa
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "communicate_through": None,
                        "created_at": "2015-10-14T07:25:53.218988Z",
                        "created_by": 53,
                        "details": {
                            "addresses": {
                                "msisdn": {"+27824440000": {"default": True}}
                            },
                            "consent": False,
                            "default_addr_type": "msisdn",
                            "lang_code": "eng_ZA",
                            "last_mc_reg_on": "clinic",
                            "mom_dob": "1999-02-21",
                            "sa_id_no": "27625249986",
                            "source": "clinic",
                        },
                        "id": "02144938-847d-4d2c-9daf-707cb864d077",
                        "operator": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                        "updated_at": "2016-10-27T19:04:03.138598Z",
                        "updated_by": 53,
                        "version": 1,
                    }
                ],
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        responses.add(
            responses.PATCH,
            "http://identitystore/identities/02144938-847d-4d2c-9daf-707cb864d077/",  # noqa
            json={
                "communicate_through": None,
                "created_at": "2015-10-14T07:25:53.218988Z",
                "created_by": 53,
                "details": {
                    "addresses": {"msisdn": {"+27824440000": {"default": True}}},
                    "consent": False,
                    "default_addr_type": "msisdn",
                    "lang_code": "eng_ZA",
                    "last_mc_reg_on": "clinic",
                    "mom_dob": "1999-02-21",
                    "sa_id_no": "27625249986",
                    "source": "clinic",
                },
                "id": "02144938-847d-4d2c-9daf-707cb864d077",
                "operator": "3a4af5d9-887b-410f-afa1-460d4b3ecc05",
                "updated_at": "2016-10-27T19:04:03.138598Z",
                "updated_by": 53,
                "version": 1,
            },
            match_querystring=True,
            status=200,
            content_type="application/json",
        )
        post_data = {
            "hcw_msisdn": "+27831111111",
            "mom_msisdn": "+27824440000",
            "mom_id_type": "none",
            "mom_passport_origin": None,
            "mom_id_no": "27625249986",
            "mom_lang": "en",
            "mom_edd": "2016-11-05",
            "mom_dob": "1999-02-21",
            "clinic_code": None,
            "authority": "chw",
            "consent": True,
        }
        # Execute
        response = self.partialclient.post(
            "/api/v1/extregistration/",
            json.dumps(post_data),
            content_type="application/json",
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, "test_source_external_partial")
        self.assertEqual(d.reg_type, "momconnect_prebirth")
        self.assertEqual(d.registrant_id, "02144938-847d-4d2c-9daf-707cb864d077")
        self.assertEqual(d.data["edd"], "2016-11-05")


class TestRegistrationValidation(AuthenticatedAPITestCase):
    def test_validate_pmtct_prebirth_good(self):
        """ Good minimal data pmtct_prebirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-08-30",
            },
        }
        registration = Registration.objects.create(**registration_data)
        with mock.patch("ndoh_hub.utils.get_today", override_get_today):
            # Execute
            v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_pmtct_prebirth_malformed_data(self):
        """ Malformed data pmtct_prebirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01",
                "language": "en",
                "mom_dob": "199-01-27",
                "edd": "201-11-30",
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Invalid UUID registrant_id",
                "Language not a valid option",
                "Mother DOB invalid",
                "Estimated Due Date invalid",
                "Operator ID invalid",
            ],
        )

    def test_validate_pmtct_prebirth_missing_data(self):
        """ Missing data pmtct_prebirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Language is missing from data",
                "Mother DOB missing",
                "Estimated Due Date missing",
                "Operator ID missing",
            ],
        )

    def test_validate_pmtct_postbirth_good(self):
        """ Good minimal data pmtct_postbirth test """
        # Setup
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
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_pmtct_postbirth_missing_data(self):
        """ Missing data pmtct_postbirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Language is missing from data",
                "Mother DOB missing",
                "Baby Date of Birth missing",
                "Operator ID missing",
            ],
        )

    def test_validate_nurseconnect_good(self):
        """ Good minimal data nurseconnect test """
        # Setup
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821112222",
                "msisdn_device": "+27821112222",
                "faccode": "123456",
                "language": "eng_ZA",
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_whatsapp_nurseconnect(self):
        """
        A valid nurseconnect registration should also be a valid whatsapp
        nurseconnect registration.
        """
        # Setup
        registration_data = {
            "reg_type": "whatsapp_nurseconnect",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821112222",
                "msisdn_device": "+27821112222",
                "faccode": "123456",
                "language": "eng_ZA",
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_nurseconnect_malformed_data(self):
        """ Malformed data nurseconnect test """
        # Setup
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "mother01",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01",
                "msisdn_registrant": "+2782111222",
                "msisdn_device": "+2782111222",
                "faccode": "123456",
                "language": "en",
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Invalid UUID registrant_id",
                "Operator ID invalid",
                "MSISDN of Registrant invalid",
                "MSISDN of device invalid",
                "Language not a valid option",
            ],
        )

    def test_validate_nurseconnect_missing_data(self):
        """ Missing data nurseconnect test """
        # Setup
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Facility (clinic) code missing",
                "Operator ID missing",
                "MSISDN of Registrant missing",
                "MSISDN of device missing",
                "Language is missing from data",
            ],
        )

    def test_validate_momconnect_prebirth_clinic_good(self):
        """ clinic momconnect_prebirth sa_id """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "mom_dob": "1982-08-01",
                "language": "eng_ZA",
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "faccode": "123456",
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_momconnect_prebirth_clinic_malformed_data_1(self):
        """ clinic momconnect_prebirth sa_id reg """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01",
                "msisdn_registrant": "+27821113",
                "msisdn_device": "+27821113",
                "id_type": "sa_id",
                "sa_id_no": "810801",
                "mom_dob": "1982",
                "language": "eng",
                "edd": "2016",
                "faccode": "",
                "consent": None,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Invalid UUID registrant_id",
                "Operator ID invalid",
                "MSISDN of Registrant invalid",
                "MSISDN of device invalid",
                "Language not a valid option",
                "Cannot continue without consent",
                "SA ID number invalid",
                "Mother DOB invalid",
                "Estimated Due Date invalid",
                "Facility code invalid",
            ],
        )

    def test_validate_momconnect_prebirth_clinic_malformed_data_2(self):
        """ clinic momconnect_prebirth passport reg """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01",
                "msisdn_registrant": "+27821113",
                "msisdn_device": "+27821113",
                "id_type": "passport",
                "passport_origin": "uruguay",
                "language": "eng",
                "edd": "2016",
                "faccode": "",
                "consent": None,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Invalid UUID registrant_id",
                "Operator ID invalid",
                "MSISDN of Registrant invalid",
                "MSISDN of device invalid",
                "Language not a valid option",
                "Cannot continue without consent",
                "Passport number missing",
                "Passport origin invalid",
                "Estimated Due Date invalid",
                "Facility code invalid",
            ],
        )

    def test_validate_momconnect_prebirth_clinic_missing_data(self):
        """ clinic momconnect_prebirth data blob missing """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01",
            "source": self.make_source_adminuser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Invalid UUID registrant_id",
                "Operator ID missing",
                "MSISDN of Registrant missing",
                "MSISDN of device missing",
                "Language is missing from data",
                "Consent is missing",
                "ID type missing",
                "Estimated Due Date missing",
                "Facility (clinic) code missing",
            ],
        )

    def test_validate_momconnect_prebirth_chw_good(self):
        """ chw momconnect_prebirth passport """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_partialuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "id_type": "passport",
                "passport_no": "abc1234",
                "passport_origin": "bw",
                "language": "zul_ZA",
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_momconnect_prebirth_chw_missing_data(self):
        """ chw momconnect_prebirth data blob missing """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_partialuser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Operator ID missing",
                "MSISDN of Registrant missing",
                "MSISDN of device missing",
                "Language is missing from data",
                "Consent is missing",
                "ID type missing",
            ],
        )

    def test_validate_momconnect_prebirth_public_good(self):
        """ public momconnect_prebirth """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "language": "zul_ZA",
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_momconnect_prebirth_public_missing_data(self):
        """ public momconnect_prebirth data blob missing """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {},
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(
            registration.data["invalid_fields"],
            [
                "Operator ID missing",
                "MSISDN of Registrant missing",
                "MSISDN of device missing",
                "Language is missing from data",
                "Consent is missing",
            ],
        )

    def test_validate_whatsapp_prebirth_public_good(self):
        """ public whatsapp_prebirth """
        # Setup
        registration_data = {
            "reg_type": "whatsapp_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "language": "zul_ZA",
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_whatsapp_pmtct_postbirth_good(self):
        """ Good minimal data whatsapp_pmtct_postbirth test """
        # Setup
        registration_data = {
            "reg_type": "whatsapp_pmtct_postbirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "baby_dob": "2016-01-01",
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_whatsapp_pmtct_prebirth_good(self):
        """ Good minimal data whatsapp_pmtct_prebirth test """
        # Setup
        registration_data = {
            "reg_type": "whatsapp_pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-08-30",
            },
        }
        registration = Registration.objects.create(**registration_data)
        with mock.patch("ndoh_hub.utils.get_today", override_get_today):
            # Execute
            v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)


class TestRegistrationCreation(AuthenticatedAPITestCase):
    def test_get_software_type_from_reg(self):
        # Setup
        source = self.make_source_normaluser()
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+27000000000",
                "msisdn_registrant": "+27111111111",
                "consent": True,
                "swt": 5,
            },
        }

        registration = Registration.objects.create(**registration_data)
        swt = PushRegistrationToJembi().get_software_type(registration)
        self.assertEqual(swt, 5)

    def test_get_software_type_normal_reg(self):
        # Setup
        source = self.make_source_normaluser()
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+27000000000",
                "msisdn_registrant": "+27111111111",
                "consent": True,
            },
        }

        registration = Registration.objects.create(**registration_data)
        swt = PushRegistrationToJembi().get_software_type(registration)
        self.assertEqual(swt, 1)

    def test_get_software_type_whatsapp_reg(self):
        # Setup
        source = self.make_source_normaluser()
        registration_data = {
            "reg_type": "whatsapp_momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+27000000000",
                "msisdn_registrant": "+27111111111",
                "consent": True,
            },
        }

        registration = Registration.objects.create(**registration_data)
        swt = PushRegistrationToJembi().get_software_type(registration)
        self.assertEqual(swt, 7)

    @responses.activate
    def test_registration_process_bad(self):
        """ Test a full registration process with bad data """
        # Setup
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # . setup pmtct_prebirth registration
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27"
                # edd is missing
            },
        }

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check registration failed to validate
        registration.refresh_from_db()
        self.assertEqual(registration.validated, False)
        self.assertEqual(
            registration.data["invalid_fields"], ["Estimated Due Date missing"]
        )

        # . check number of calls made
        self.assertEqual(len(responses.calls), 0)

        # . check no subscriptionrequest objects were created
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    def test_push_nurseconnect_registration_to_jembi_get_software_type(self):
        """
        If a software type is specified, that software type should be used.
        If not, if it's a whatsapp registration, then a software type of 7
        should be used.
        If not, then the default software type of 3 should be used.
        """
        source = Source.objects.create(
            name="NURSE USSD App",
            authority="hw_full",
            user=User.objects.get(username="testadminuser"),
        )
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "nurseconnect-identity",
            "source": source,
            "data": {
                "operator_id": "nurseconnect-identity",
                "msisdn_registrant": "+27821112222",
                "msisdn_device": "+27821112222",
                "faccode": "123456",
                "language": "eng_ZA",
            },
        }
        registration = Registration.objects.create(**registration_data)

        # Default software type
        self.assertEqual(
            push_nurse_registration_to_jembi.get_software_type(registration), 3
        )

        # WhatsApp registration software type
        registration.reg_type = "whatsapp_nurseconnect"
        registration.save()

        self.assertEqual(
            push_nurse_registration_to_jembi.get_software_type(registration), 7
        )

        # Specified software type
        registration.data["swt"] = 2
        registration.save()

        self.assertEqual(
            push_nurse_registration_to_jembi.get_software_type(registration), 2
        )


class TestFixPmtctRegistrationsCommand(AuthenticatedAPITestCase):
    @responses.activate
    @mock.patch("ndoh_hub.utils.get_today", return_value=override_get_today())
    def test_fix_pmtct_registrations(self, mock_today):
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_id("mother02-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother02-63e2-4acc-9b94-26663b9bc267")

        # create the previous momconnect registration
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "edd": "2016-08-01",
                "mom_dob": "1982-08-01",
                "language": "eng_ZA",
                "operator_id": "operator-123456",
                "test": "test",
            },
            "source": self.make_source_normaluser(),
            "validated": True,
        }
        Registration.objects.create(**data)
        data["registrant_id"] = "mother02-63e2-4acc-9b94-26663b9bc267"
        Registration.objects.create(**data)

        # create the failed pmtct regsitration
        data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "mom_dob": "1987-04-24",
                "invalid_fields": ["Estimated Due Date missing"],
                "language": "eng_ZA",
            },
            "source": self.make_source_normaluser(),
        }
        Registration.objects.create(**data)
        data["registrant_id"] = "mother02-63e2-4acc-9b94-26663b9bc267"
        data["data"]["operator_id"] = "mother02-63e2-4acc-9b94-26663b9bc267"
        check_registration = Registration.objects.create(**data)

        stdout = StringIO()
        call_command("fix_pmtct_registrations", stdout=stdout)

        check_registration = Registration.objects.get(id=check_registration.id)

        self.assertEqual(
            stdout.getvalue().strip(), "2 registrations fixed and validated."
        )
        self.assertEqual(check_registration.data.get("edd"), "2016-08-01")
        self.assertEqual(check_registration.validated, True)


class TestJembiHelpdeskOutgoing(AuthenticatedAPITestCase):
    def setUp(self):
        super(TestJembiHelpdeskOutgoing, self).setUp()
        self.inbound_created_on_date = datetime.datetime.strptime(
            "2016-01-01", "%Y-%m-%d"
        )
        self.outbound_created_on_date = datetime.datetime.strptime(
            "2016-01-02", "%Y-%m-%d"
        )

    def tearDown(self):
        super(TestJembiHelpdeskOutgoing, self).tearDown()
        cache.clear()

    def make_registration_for_jembi_helpdesk(self, source=None):
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source or self.make_source_normaluser(),
            "data": {
                "operator_id": "operator-123456",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "mom_dob": "1982-08-01",
                "language": "eng_ZA",
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "faccode": "123456",
                "consent": True,
            },
        }
        return Registration.objects.create(**registration_data)

    @responses.activate
    def test_send_outgoing_message_to_jembi(self):
        message_id = 10
        jembi_url = "http://jembi/ws/rest/v1/nc/helpdesk"
        self.make_registration_for_jembi_helpdesk()
        utils_tests.mock_request_to_jembi_api(jembi_url)

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        utils_tests.mock_junebug_channel_call(
            "http://junebug/jb/channels/6a5c691e-140c-48b0-9f39-a53d4951d7fa", "sms"
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "inbound_channel_id": "6a5c691e-140c-48b0-9f39-a53d4951d7fa",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 2)
        request_json = json.loads(responses.calls[1].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 2)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

    @responses.activate
    @override_settings(ENABLE_JEMBI_EVENTS=False)
    def test_no_send_to_jembi(self):
        message_id = 10
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_junebug_channel_call(
            "http://junebug/jb/channels/6a5c691e-140c-48b0-9f39-a53d4951d7fa", "sms"
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "inbound_channel_id": "6a5c691e-140c-48b0-9f39-a53d4951d7fa",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_send_outgoing_message_to_jembi_nurseconnect(self):
        message_id = 10
        source = self.make_source_normaluser("NURSE Helpdesk App")
        self.make_registration_for_jembi_helpdesk(source)

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/nc/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        utils_tests.mock_junebug_channel_call(
            "http://junebug/jb/channels/6a5c691e-140c-48b0-9f39-a53d4951d7fa", "sms"
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "inbound_channel_id": "6a5c691e-140c-48b0-9f39-a53d4951d7fa",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 2)
        request_json = json.loads(responses.calls[1].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 2)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 12)
        self.assertEqual(request_json["op"], "1234")

    @responses.activate
    def test_send_outgoing_message_to_jembi_with_null_operator_id(self):
        message_id = 10
        reg = self.make_registration_for_jembi_helpdesk()
        reg.data["operator_id"] = None
        reg.save()

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 2)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

    @responses.activate
    def test_send_outgoing_message_to_jembi_invalid_user_id(self):
        message_id = 10
        user_id = "unknown-uuid"
        jembi_url = "http://jembi/ws/rest/v1/helpdesk"
        self.make_source_normaluser()

        utils_tests.mock_jembi_json_api_call(
            url=jembi_url,
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": user_id,
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["sid"], user_id)
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 2)
        self.assertEqual(request_json["faccode"], None)
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

    @responses.activate
    def test_send_outgoing_message_to_jembi_with_blank_values(self):
        message_id = 10
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 2)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {"answer": u"this is a sample response", "question": ""},
        )
        self.assertEqual(request_json["class"], "Unclassified")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

        [sub] = JembiSubmission.objects.all()
        self.assertEqual(sub.path, "helpdesk")
        self.maxDiff = None
        self.assertEqual(
            sub.request_data,
            {
                "dmsisdn": "+27123456789",
                "cmsisdn": "+27123456789",
                "eid": str(UUID(int=message_id)),
                "sid": "mother01-63e2-4acc-9b94-26663b9bc267",
                "encdate": "20160101000000",
                "repdate": "20160102000000",
                "mha": 1,
                "swt": 2,
                "faccode": "123456",
                "data": {"question": "", "answer": "this is a sample response"},
                "class": "Unclassified",
                "type": 7,
                "op": "1234",
            },
        )
        self.assertEqual(sub.submitted, True)
        self.assertEqual(sub.response_status_code, 201)
        self.assertEqual(sub.response_headers, {"Content-Type": "text/plain"})
        self.assertEqual(sub.response_body, '{"result": "jembi-is-ok"}')

    @responses.activate
    def test_send_outgoing_message_to_jembi_via_whatsapp(self):
        message_id = 10
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        utils_tests.mock_junebug_channel_call(
            "http://junebug/jb/channels/6a5c691e-140c-48b0-9f39-a53d4951d7fa", "wassup"
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "inbound_channel_id": "6a5c691e-140c-48b0-9f39-a53d4951d7fa",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 2)
        request_json = json.loads(responses.calls[1].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 4)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

        cache_key = "SW_TYPE_6a5c691e-140c-48b0-9f39-a53d4951d7fa"
        self.assertEqual(cache.get(cache_key), 4)

    @responses.activate
    def test_send_outgoing_message_to_jembi_using_cache_for_sw_type(self):
        message_id = 10
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/helpdesk",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={},
        )

        cache_key = "SW_TYPE_6a5c691e-140c-48b0-9f39-a53d4951d7fa"
        cache.set(cache_key, 4)

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
            "inbound_channel_id": "6a5c691e-140c-48b0-9f39-a53d4951d7fa",
            "message_id": message_id,
        }
        # Execute
        response = self.normalclient.post(
            "/api/v1/jembi/helpdesk/outgoing/", user_request
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json["dmsisdn"], "+27123456789")
        self.assertEqual(request_json["cmsisdn"], "+27123456789")
        self.assertEqual(request_json["eid"], str(UUID(int=message_id)))
        self.assertEqual(request_json["encdate"], "20160101000000")
        self.assertEqual(request_json["repdate"], "20160102000000")
        self.assertEqual(request_json["mha"], 1)
        self.assertEqual(request_json["swt"], 4)
        self.assertEqual(request_json["faccode"], "123456")
        self.assertEqual(
            request_json["data"],
            {
                "question": u"this is a sample user message",
                "answer": u"this is a sample response",
            },
        )
        self.assertEqual(request_json["class"], "Complaint")
        self.assertEqual(request_json["type"], 7)
        self.assertEqual(request_json["op"], "1234")

    @responses.activate
    def test_report_pmtct_registrations(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111"},
        )

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username="testnormaluser"),
        )

        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "0000000000",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+2700000000",
                "msisdn_registrant": "+27111111111",
            },
        }

        registration = Registration.objects.create(**registration_data)
        # NOTE: we're faking validation step here
        registration.validated = True
        registration.save()

        stdout = StringIO()
        call_command("report_pmtct_registrations", stdout=stdout)

        self.assertEqual(
            stdout.getvalue().strip(),
            "\r\n".join(
                [
                    "Registration Type,created,count",
                    "pmtct_prebirth,%s,1" % (timezone.now().strftime("%Y-%m-%d"),),
                ]
            ),
        )

    @responses.activate
    def test_report_pmtct_risks(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111"},
        )

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username="testnormaluser"),
        )

        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "0000000000",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+2700000000",
                "msisdn_registrant": "+27111111111",
            },
        }

        registration = Registration.objects.create(**registration_data)
        # NOTE: we're faking validation step here
        registration.validated = True
        registration.save()

        # Add a registration that is not validated
        registration = Registration.objects.create(**registration_data)
        registration.save()

        stdout = StringIO()
        call_command("report_pmtct_risks", stdout=stdout)

        self.assertEqual(
            stdout.getvalue().strip(), "\r\n".join(["risk,count", "high,1"])
        )

    @responses.activate
    def test_report_pmtct_risks_hub(self):

        registrations = [
            {
                "created_at": "created-at",
                "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "reg_type": "pmtct_postbirth",
                "data": {"mom_dob": "dob", "edd": "edd"},
            }
        ] * 2

        responses.add(
            responses.GET,
            "http://hub.example.com/api/v1/registrations/?source=1&validated=True",  # noqa
            match_querystring=True,
            json={"next": None, "results": registrations},
            status=200,
            content_type="application/json",
        )

        responses.add(
            responses.GET,
            "http://hub.example.com/api/v1/registrations/?source=3&validated=True",  # noqa
            match_querystring=True,
            json={"next": None, "results": []},
            status=200,
            content_type="application/json",
        )

        stdout = StringIO()
        call_command(
            "report_pmtct_risks",
            "--hub-url",
            "http://hub.example.com/api/v1/",
            "--hub-token",
            "hub_token",
            stdout=stdout,
        )

        self.assertEqual(
            stdout.getvalue().strip(), "\r\n".join(["risk,count", "high,2"])
        )

    @responses.activate
    def test_report_pmtct_risks_by_msisdn(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111"},
        )

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username="testnormaluser"),
        )

        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "id_type": "sa_id",
                "sa_id_no": "0000000000",
                "edd": "2016-11-30",
                "faccode": "123456",
                "msisdn_device": "+2700000000",
                "msisdn_registrant": "+27111111111",
            },
        }

        registration = Registration.objects.create(**registration_data)
        # NOTE: we're faking validation step here
        registration.validated = True
        registration.save()

        responses.add(
            responses.GET,
            "http://idstore.example.com/api/v1/identities/{}/".format(
                registration.registrant_id
            ),
            json={
                "identity": registration.registrant_id,
                "details": {
                    "personnel_code": "personnel_code",
                    "facility_name": "facility_name",
                    "default_addr_type": "msisdn",
                    "receiver_role": "role",
                    "state": "state",
                    "addresses": {"msisdn": {"+27111111111": {}}},
                },
            },
            status=200,
            content_type="application/json",
        )

        stdout = StringIO()
        call_command(
            "report_pmtct_risks",
            "--group",
            "msisdn",
            "--identity-store-url",
            "http://idstore.example.com/api/v1/",
            "--identity-store-token",
            "identitystore_token",
            stdout=stdout,
        )

        self.assertEqual(
            stdout.getvalue().strip(), "\r\n".join(["msisdn,risk", "+27111111111,1"])
        )


class TestMetricsAPI(AuthenticatedAPITestCase):
    def test_metrics_read(self):
        # Setup
        self.make_source_normaluser()
        self.make_source_adminuser()
        # Execute
        response = self.adminclient.get(
            "/api/metrics/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["metrics_available"], [])

    @responses.activate
    def test_post_metrics(self):
        # Setup
        responses.add(
            responses.POST,
            "http://metrics-url/metrics/",
            json={"foo": "bar"},
            status=200,
            content_type="application/json",
        )
        # Execute
        response = self.adminclient.post(
            "/api/metrics/", content_type="application/json"
        )
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["scheduled_metrics_initiated"], True)


class UpdateInitialSequenceCommand(AuthenticatedAPITestCase):
    def test_command_requires_sbm_url(self):
        with self.assertRaises(management.CommandError) as ce:
            management.call_command("update_initial_sequence")
        self.assertEqual(
            str(ce.exception),
            "Please make sure either the "
            "STAGE_BASED_MESSAGING_URL environment variable or --sbm-url is "
            "set.",
        )

    def test_command_requires_sbm_token(self):
        with self.assertRaises(management.CommandError) as ce:
            management.call_command(
                "update_initial_sequence", sbm_url="http://example.com"
            )
        self.assertEqual(
            str(ce.exception),
            "Please make sure either the "
            "STAGE_BASED_MESSAGING_TOKEN environment variable or --sbm-token "
            "is set.",
        )

    @responses.activate
    def test_update_initial_sequence(self):
        stdout, stderr = StringIO(), StringIO()

        registration = self.make_registration_normaluser()

        SubscriptionRequest.objects.create(
            identity=str(registration.registrant_id),
            messageset=3,
            next_sequence_number=2,
            lang="eng_ZA",
        )

        responses.add(
            responses.GET,
            "http://localhost:8005/api/v1/subscriptions/",
            json={
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": "b0afe9fb-0b4d-478e-974e-6b794e69cc6e",
                        "version": 1,
                        "identity": "mother00-9d89-4aa6-99ff-13c225365b5d",
                        "messageset": 1,
                        "next_sequence_number": 1,
                        "lang": "eng",
                        "active": True,
                        "completed": False,
                        "schedule": 1,
                        "process_status": 0,
                        "metadata": None,
                        "created_at": "2017-01-16",
                    }
                ],
            },
            status=200,
            content_type="application/json",
            match_querystring=False,
        )

        responses.add(
            responses.PATCH,
            "http://localhost:8005/api/v1/subscriptions/b0afe9fb-0b4d-478e-974e-6b794e69cc6e/",  # noqa
            json={"active": False},
            status=200,
            content_type="application/json",
            match_querystring=True,
        )

        management.call_command(
            "update_initial_sequence",
            sbm_url="http://localhost:8005/api/v1",
            sbm_token="test_token",
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue().strip(), "Updated 1 subscriptions.")

    @responses.activate
    def test_update_initial_sequence_no_sub(self):
        stdout, stderr = StringIO(), StringIO()

        registration = self.make_registration_normaluser()

        SubscriptionRequest.objects.create(
            identity=str(registration.registrant_id),
            messageset=3,
            next_sequence_number=2,
            lang="eng_ZA",
        )

        responses.add(
            responses.GET,
            "http://localhost:8005/api/v1/subscriptions/",
            json={"next": None, "previous": None, "results": []},
            status=200,
            content_type="application/json",
            match_querystring=False,
        )

        management.call_command(
            "update_initial_sequence",
            sbm_url="http://localhost:8005/api/v1",
            sbm_token="test_token",
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            stdout.getvalue().strip(),
            "Subscription not found: {}\nUpdated 0 subscriptions.".format(
                registration.registrant_id
            ),
        )


class TestRemovePersonallyIdentifiableFieldsTask(AuthenticatedAPITestCase):
    @responses.activate
    def test_fields_are_removed(self):
        """
        Confirms that all fields that are considered as personal information
        fields are removed from the registration, and placed on the identity.

        Any fields on the registration that are not considered personal
        information should remain, and not be placed on the identity.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={
                "id_type": "passport",
                "passport_origin": "na",
                "passport_no": "1234",
                "sa_id_no": "4321",
                "language": "eng_ZA",
                "consent": True,
                "foo": "baz",
            },
        )

        utils_tests.mock_get_identity_by_id("mother-uuid")
        utils_tests.mock_patch_identity("mother-uuid")

        remove_personally_identifiable_fields(str(registration.pk))

        identity_update = json.loads(responses.calls[-1].request.body)
        self.assertEqual(
            identity_update,
            {
                "details": {
                    "id_type": "passport",
                    "passport_origin": "na",
                    "passport_no": "1234",
                    "sa_id_no": "4321",
                    "lang_code": "eng_ZA",
                    "consent": True,
                    "foo": "bar",
                }
            },
        )

        registration.refresh_from_db()
        self.assertEqual(registration.data, {"foo": "baz"})

    @responses.activate
    def test_msisdns_are_replaced_with_uuid(self):
        """
        Confirms that all msisdn fields are replaced with the relevant UUIDs
        for the identity that represents that msisdn.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={"msisdn_device": "+1234", "msisdn_registrant": "+4321"},
        )

        utils_tests.mock_get_identity_by_msisdn("+1234", "device-uuid")
        utils_tests.mock_get_identity_by_msisdn("+4321", "registrant-uuid")

        remove_personally_identifiable_fields(str(registration.pk))

        registration.refresh_from_db()
        self.assertEqual(
            registration.data,
            {"uuid_device": "device-uuid", "uuid_registrant": "registrant-uuid"},
        )

    @responses.activate
    def test_msisdns_are_replaced_with_uuid_no_identity(self):
        """
        If no identity exists for a given msisdn, then one should be created,
        and that UUID should be used to replace the msisdn.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={"msisdn_device": "+1234"},
        )

        utils_tests.mock_get_identity_by_msisdn("+1234", num=0)
        utils_tests.mock_create_identity("uuid-1234")

        remove_personally_identifiable_fields(str(registration.pk))

        identity_creation = json.loads(responses.calls[-1].request.body)
        self.assertEqual(
            identity_creation, {"details": {"addresses": {"msisdn": {"+1234": {}}}}}
        )

        registration.refresh_from_db()
        self.assertEqual(registration.data, {"uuid_device": "uuid-1234"})


class TestAddPersonallyIdentifiableFields(AuthenticatedAPITestCase):
    @responses.activate
    def test_identity_doesnt_exist(self):
        """
        If the identity for a registration doesn't exist, then we can't pull
        any information from it, so we have to return the registration
        unchanged.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={},
        )

        utils_tests.mock_get_nonexistant_identity_by_id("mother-uuid")

        registration = add_personally_identifiable_fields(registration)

        self.assertEqual(
            registration.data, Registration.objects.get(pk=str(registration.id)).data
        )

    @responses.activate
    def test_identity_fields_get_set(self):
        """
        If the fields are on the identity, they should get set on the returned
        registration object.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={},
        )

        utils_tests.mock_get_identity_by_id(
            "mother-uuid",
            {
                "id_type": "passport",
                "passport_origin": "na",
                "passport_no": "1234",
                "sa_id_no": "4321",
                "lang_code": "eng_ZA",
                "consent": True,
                "foo": "baz",
            },
        )

        registration = add_personally_identifiable_fields(registration)

        self.assertEqual(
            registration.data,
            {
                "id_type": "passport",
                "passport_origin": "na",
                "passport_no": "1234",
                "sa_id_no": "4321",
                "language": "eng_ZA",
                "consent": True,
            },
        )

    @responses.activate
    def test_identity_uuid_fields_get_set(self):
        """
        The msisdn fields that were replaced with UUID fields, should now
        be replaced with the original MSISDN fields.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={"uuid_device": "uuid-device", "uuid_registrant": "uuid-registrant"},
        )

        utils_tests.mock_get_identity_by_id("mother-uuid")
        utils_tests.mock_get_identity_by_id(
            "uuid-device",
            {
                "addresses": {
                    "msisdn": {
                        "msisdn-device": {},
                        "msisdn-incorrect": {"optedout": True},
                    }
                }
            },
        )
        utils_tests.mock_get_identity_by_id(
            "uuid-registrant",
            {
                "addresses": {
                    "msisdn": {
                        "msisdn-incorrect-1": {},
                        "msisdn-registrant": {"default": True},
                        "msisdn-incorrect-2": {},
                    }
                }
            },
        )

        registration = add_personally_identifiable_fields(registration)

        self.assertEqual(
            registration.data,
            {
                "uuid_device": "uuid-device",
                "uuid_registrant": "uuid-registrant",
                "msisdn_device": "msisdn-device",
                "msisdn_registrant": "msisdn-registrant",
                "language": "afr_ZA",
            },
        )

    @responses.activate
    def test_identity_uuid_fields_missing_identity(self):
        """
        If one of the UUID fields's identity is missing, then we cannot set
        the msisdn field.
        """
        registration = Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            source=self.make_source_normaluser(),
            validated=True,
            data={"uuid_device": "uuid-device"},
        )

        utils_tests.mock_get_identity_by_id("mother-uuid")
        utils_tests.mock_get_nonexistant_identity_by_id("uuid-device")

        registration = add_personally_identifiable_fields(registration)

        self.assertEqual(
            registration.data, {"uuid_device": "uuid-device", "language": "afr_ZA"}
        )
