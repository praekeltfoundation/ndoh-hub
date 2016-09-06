import json
import uuid
import datetime
import responses

from django.contrib.auth.models import User
from django.test import TestCase
from django.db.models.signals import post_save
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_hooks.models import model_saved

from .models import (Source, Registration, SubscriptionRequest,
                     psh_validate_subscribe)
from .tasks import validate_subscribe, get_risk_status
from ndoh_hub import utils, utils_tests


def override_get_today():
    return datetime.datetime.strptime("2016-01-01", "%Y-%m-%d")


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

    def test_get_pregnancy_week(self):
        t = override_get_today()

        # Test around 40 weeks
        self.assertEqual(utils.get_pregnancy_week(t, "2015-12-19"), 42)
        self.assertEqual(utils.get_pregnancy_week(t, "2015-12-25"), 41)
        self.assertEqual(utils.get_pregnancy_week(t, "2015-12-31"), 41)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-01-01"), 40)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-01-07"), 40)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-01-08"), 39)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-01-14"), 39)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-01-15"), 38)

        # Test around first weeks
        self.assertEqual(utils.get_pregnancy_week(t, "2016-09-22"), 3)
        self.assertEqual(utils.get_pregnancy_week(t, "2016-09-23"), 2)
        # . never less than 2
        self.assertEqual(utils.get_pregnancy_week(t, "2100-01-01"), 2)

    def test_get_baby_age(self):
        t = override_get_today()

        # Test baby birth date that is in the future - should never happen
        self.assertEqual(utils.get_baby_age(t, "2016-01-02"), -1)
        # Test same day
        self.assertEqual(utils.get_baby_age(t, "2016-01-01"), 0)
        # Test first week transition
        self.assertEqual(utils.get_baby_age(t, "2015-12-26"), 0)
        self.assertEqual(utils.get_baby_age(t, "2015-12-25"), 1)

    def test_get_messageset_short_name(self):
        # any reg_type non-prebirth and non-postbirth
        self.assertEqual(
            utils.get_messageset_short_name("reg_type", "authority", 9000),
            "reg_type.authority.1")

        # pmtct prebirth testing
        # week -1000 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", -1000),
            "pmtct_prebirth.authority.1")
        # week 1 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 1),
            "pmtct_prebirth.authority.1")
        # week 29 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 29),
            "pmtct_prebirth.authority.1")
        # week 30 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 30),
            "pmtct_prebirth.authority.2")
        # week 34 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 34),
            "pmtct_prebirth.authority.2")
        # week 35 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 35),
            "pmtct_prebirth.authority.3")
        # week 1000 prebirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_prebirth", "authority", 1000),
            "pmtct_prebirth.authority.3")

        # pmtct postbirth testing
        # week -1000 postbirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_postbirth", "authority", -1000),
            "pmtct_postbirth.authority.1")
        # week 0 postbirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_postbirth", "authority", 0),
            "pmtct_postbirth.authority.1")
        # week 1 postbirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_postbirth", "authority", 1),
            "pmtct_postbirth.authority.1")
        # week 2 postbirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_postbirth", "authority", 2),
            "pmtct_postbirth.authority.2")
        # week 1000 postbirth
        self.assertEqual(utils.get_messageset_short_name(
            "pmtct_postbirth", "authority", 1000),
            "pmtct_postbirth.authority.2")

        # nurseconnect testing
        self.assertEqual(utils.get_messageset_short_name(
            "nurseconnect", "authority", 500),
            "nurseconnect.authority.1")

        # momconnect prebirth testing
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", -1000),
            "momconnect_prebirth.hw_full.1")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 0),
            "momconnect_prebirth.hw_full.1")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 30),
            "momconnect_prebirth.hw_full.1")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 31),
            "momconnect_prebirth.hw_full.2")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 35),
            "momconnect_prebirth.hw_full.2")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 36),
            "momconnect_prebirth.hw_full.3")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 37),
            "momconnect_prebirth.hw_full.4")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 38),
            "momconnect_prebirth.hw_full.5")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 39),
            "momconnect_prebirth.hw_full.6")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "hw_full", 1000),
            "momconnect_prebirth.hw_full.6")

        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "authority", -1000),
            "momconnect_prebirth.authority.1")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "authority", 35),
            "momconnect_prebirth.authority.1")
        self.assertEqual(utils.get_messageset_short_name(
            "momconnect_prebirth", "authority", 1000),
            "momconnect_prebirth.authority.1")

    @responses.activate
    def test_get_messageset_schedule_sequence(self):
        # Setup all fixture responses
        # . pmtct
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.2")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.3")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.2")
        utils_tests.mock_get_schedule(schedule_id)

        # . nurseconnect
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)

        # . momconnect
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.2")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.3")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.4")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.5")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.6")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_partial.1")
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Check pmtct prebirth
        # . batch 1
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.1", 2), (11, 111, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.1", 7), (11, 111, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.1", 8), (11, 111, 2))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.1", 29), (11, 111, 23))
        # . batch 2
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.2", 30), (12, 112, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.2", 31), (12, 112, 2))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.2", 32), (12, 112, 4))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.2", 34), (12, 112, 8))
        # . batch 3
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.3", 35), (13, 113, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.3", 36), (13, 113, 3))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.3", 37), (13, 113, 6))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.3", 41), (13, 113, 18))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_prebirth.patient.3", 42), (13, 113, 20))

        # Check pmtct postbirth
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_postbirth.patient.1", 0), (14, 114, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_postbirth.patient.1", 1), (14, 114, 3))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_postbirth.patient.2", 2), (15, 115, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_postbirth.patient.2", 3), (15, 115, 2))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "pmtct_postbirth.patient.2", 4), (15, 115, 3))

        # Check nurseconnect
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "nurseconnect.hw_full.1", 500), (61, 161, 1))

        # Check momconnect prebirth
        # . clinic
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.1", 0), (21, 121, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.1", 5), (21, 121, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.1", 6), (21, 121, 3))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.1", 30), (21, 121, 51))

        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.2", 31), (22, 122, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.2", 32), (22, 122, 4))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.2", 35), (22, 122, 13))

        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.3", 36), (23, 123, 1))

        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.4", 37), (24, 124, 1))

        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.5", 38), (25, 125, 1))

        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.6", 39), (26, 126, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_full.6", 42), (26, 126, 1))

        # . public
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.patient.1", 0), (41, 141, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.patient.1", 40), (41, 141, 1))

        # . chw
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_partial.1", 0), (42, 142, 1))
        self.assertEqual(utils.get_messageset_schedule_sequence(
            "momconnect_prebirth.hw_partial.1", 40), (42, 142, 1))


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
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(receiver=psh_validate_subscribe,
                             sender=Registration)
        post_save.disconnect(receiver=model_saved,
                             dispatch_uid='instance-saved-hook')
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
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

    def make_source_partialuser(self):
        data = {
            "name": "test_source_partialuser",
            "authority": "hw_partial",
            "user": User.objects.get(username='testpartialuser')
        }
        return Source.objects.create(**data)

    def make_source_normaluser(self):
        data = {
            "name": "test_source_normaluser",
            "authority": "patient",
            "user": User.objects.get(username='testnormaluser')
        }
        return Source.objects.create(**data)

    def make_registration_adminuser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_adminuser_reg_key": "test_adminuser_reg_value"},
            "source": self.make_source_adminuser()
        }
        return Registration.objects.create(**data)

    def make_registration_normaluser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_normaluser_reg_key": "test_normaluser_reg_value"},
            "source": self.make_source_normaluser()
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
            "validated": True
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
                "baby_dob": "2016-01-01"
            },
            "validated": False
        }
        registration2 = Registration.objects.create(**registration2_data)

        return (registration1, registration2)

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self._replace_post_save_hooks()

        # Normal User setup
        self.normalusername = 'testnormaluser'
        self.normalpassword = 'testnormalpass'
        self.normaluser = User.objects.create_user(
            self.normalusername,
            'testnormaluser@example.com',
            self.normalpassword)
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken
        self.normalclient.credentials(
            HTTP_AUTHORIZATION='Token %s' % self.normaltoken)

        # Admin User setup
        self.adminusername = 'testadminuser'
        self.adminpassword = 'testadminpass'
        self.adminuser = User.objects.create_superuser(
            self.adminusername,
            'testadminuser@example.com',
            self.adminpassword)
        admintoken = Token.objects.create(user=self.adminuser)
        self.admintoken = admintoken
        self.adminclient.credentials(
            HTTP_AUTHORIZATION='Token %s' % self.admintoken)

        # Partial User setup
        self.partialusername = 'testpartialuser'
        self.partialpassword = 'testpartialpass'
        self.partialuser = User.objects.create_user(
            self.partialusername,
            'testpartialuser@example.com',
            self.partialpassword)
        partialtoken = Token.objects.create(user=self.partialuser)
        self.partialtoken = partialtoken
        self.partialclient.credentials(
            HTTP_AUTHORIZATION='Token %s' % self.partialtoken)

    def tearDown(self):
        self._restore_post_save_hooks()


class TestLogin(AuthenticatedAPITestCase):

    def test_login_normaluser(self):
        """ Test that normaluser can login successfully
        """
        # Setup
        post_auth = {"username": "testnormaluser",
                     "password": "testnormalpass"}
        # Execute
        request = self.client.post(
            '/api/token-auth/', post_auth)
        token = request.data.get('token', None)
        # Check
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(
            request.status_code, 200,
            "Status code on /api/token-auth was %s (should be 200)."
            % request.status_code)

    def test_login_adminuser(self):
        """ Test that adminuser can login successfully
        """
        # Setup
        post_auth = {"username": "testadminuser",
                     "password": "testadminpass"}
        # Execute
        request = self.client.post(
            '/api/token-auth/', post_auth)
        token = request.data.get('token', None)
        # Check
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(
            request.status_code, 200,
            "Status code on /api/token-auth was %s (should be 200)."
            % request.status_code)

    def test_login_adminuser_wrong_password(self):
        """ Test that adminuser cannot log in with wrong password
        """
        # Setup
        post_auth = {"username": "testadminuser",
                     "password": "wrongpass"}
        # Execute
        request = self.client.post(
            '/api/token-auth/', post_auth)
        token = request.data.get('token', None)
        # Check
        self.assertIsNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_otheruser(self):
        """ Test that an unknown user cannot log in
        """
        # Setup
        post_auth = {"username": "testotheruser",
                     "password": "testotherpass"}
        # Execute
        request = self.otherclient.post(
            '/api/token-auth/', post_auth)
        token = request.data.get('token', None)
        # Check
        self.assertIsNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)


class TestUserCreation(AuthenticatedAPITestCase):

    def test_create_user_and_token(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.adminclient.post('/api/v1/user/token/', user_request)
        token = request.json().get('token', None)
        # Check
        self.assertIsNotNone(
            token, "Could not receive authentication token on post.")
        self.assertEqual(
            request.status_code, 201,
            "Status code on /api/v1/user/token/ was %s (should be 201)."
            % request.status_code)

    def test_create_user_and_token_fail_nonadmin(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.normalclient.post('/api/v1/user/token/', user_request)
        error = request.json().get('detail', None)
        # Check
        self.assertIsNotNone(
            error, "Could not receive error on post.")
        self.assertEqual(
            error, "You do not have permission to perform this action.",
            "Error message was unexpected: %s."
            % error)

    def test_create_user_and_token_not_created(self):
        # Setup
        user_request = {"email": "test@example.org"}
        # Execute
        request = self.adminclient.post('/api/v1/user/token/', user_request)
        token = request.json().get('token', None)
        # And again, to get the same token
        request2 = self.adminclient.post('/api/v1/user/token/', user_request)
        token2 = request2.json().get('token', None)

        # Check
        self.assertEqual(
            token, token2,
            "Tokens are not equal, should be the same as not recreated.")

    def test_create_user_new_token_nonadmin(self):
        # Setup
        user_request = {"email": "test@example.org"}
        request = self.adminclient.post('/api/v1/user/token/', user_request)
        token = request.json().get('token', None)
        cleanclient = APIClient()
        cleanclient.credentials(HTTP_AUTHORIZATION='Token %s' % token)
        # Execute
        request = cleanclient.post('/api/v1/user/token/', user_request)
        error = request.json().get('detail', None)
        # Check
        # new user should not be admin
        self.assertIsNotNone(
            error, "Could not receive error on post.")
        self.assertEqual(
            error, "You do not have permission to perform this action.",
            "Error message was unexpected: %s."
            % error)


class TestSourceAPI(AuthenticatedAPITestCase):

    def test_get_source_adminuser(self):
        # Setup
        source = self.make_source_adminuser()
        # Execute
        response = self.adminclient.get('/api/v1/source/%s/' % source.id,
                                        format='json',
                                        content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authority"], "hw_full")
        self.assertEqual(response.data["name"], "test_source_adminuser")

    def test_get_source_normaluser(self):
        # Setup
        source = self.make_source_normaluser()
        # Execute
        response = self.normalclient.get('/api/v1/source/%s/' % source.id,
                                         content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_source_adminuser(self):
        # Setup
        user = User.objects.get(username='testadminuser')
        post_data = {
            "name": "test_source_name",
            "authority": "patient",
            "user": "/api/v1/user/%s/" % user.id
        }
        # Execute
        response = self.adminclient.post('/api/v1/source/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        d = Source.objects.last()
        self.assertEqual(d.name, 'test_source_name')
        self.assertEqual(d.authority, "patient")

    def test_create_source_normaluser(self):
        # Setup
        user = User.objects.get(username='testnormaluser')
        post_data = {
            "name": "test_source_name",
            "authority": "hw_full",
            "user": "/api/v1/user/%s/" % user.id
        }
        # Execute
        response = self.normalclient.post('/api/v1/source/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestRegistrationAPI(AuthenticatedAPITestCase):

    def test_get_registration_adminuser(self):
        # Setup
        registration = self.make_registration_adminuser()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registration/%s/' % registration.id,
            content_type='application/json')
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_registration_normaluser(self):
        # Setup
        registration = self.make_registration_normaluser()
        # Execute
        response = self.normalclient.get(
            '/api/v1/registration/%s/' % registration.id,
            content_type='application/json')
        # Check
        # Currently only posts are allowed
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_registration_adminuser(self):
        # Setup
        self.make_source_adminuser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_key1": "test_value1"}
        }
        # Execute
        response = self.adminclient.post('/api/v1/registration/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, 'test_source_adminuser')
        self.assertEqual(d.reg_type, 'momconnect_prebirth')
        self.assertEqual(d.registrant_id,
                         "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.validated, False)
        self.assertEqual(d.data, {"test_key1": "test_value1"})
        self.assertEqual(d.created_by, self.adminuser)

    def test_create_registration_normaluser(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {"test_key1": "test_value1"}
        }
        # Execute
        response = self.normalclient.post('/api/v1/registration/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, 'test_source_normaluser')
        self.assertEqual(d.reg_type, 'momconnect_prebirth')
        self.assertEqual(d.registrant_id,
                         "mother01-63e2-4acc-9b94-26663b9bc267")
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
            "validated": True
        }
        # Execute
        response = self.normalclient.post('/api/v1/registration/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, 'test_source_normaluser')
        self.assertEqual(d.reg_type, 'momconnect_prebirth')
        self.assertEqual(d.registrant_id,
                         "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(d.validated, False)  # Should ignore True post_data
        self.assertEqual(d.data, {"test_key1": "test_value1"})

    def test_list_registrations(self):
        # Setup
        registration1 = self.make_registration_normaluser()
        registration2 = self.make_registration_adminuser()
        # Execute
        response = self.normalclient.get(
            '/api/v1/registrations/', content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        result1, result2 = response.data["results"]
        self.assertEqual(result1["id"], str(registration1.id))
        self.assertEqual(result2["id"], str(registration2.id))

    def test_filter_registration_registrant_id(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?registrant_id=%s' % (
                registration1.registrant_id),
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_reg_type(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?reg_type=%s' % registration2.reg_type,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_validated(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?validated=%s' % registration1.validated,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_source(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?source=%s' % registration2.source.id,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_created_after(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # While the '+00:00' is valid according to ISO 8601, the version of
        # django-filter we are using does not support it
        date_string = registration2.created_at.isoformat().replace(
            "+00:00", "Z")
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?created_after=%s' % date_string,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration2.id))

    def test_filter_registration_created_before(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # While the '+00:00' is valid according to ISO 8601, the version of
        # django-filter we are using does not support it
        date_string = registration1.created_at.isoformat().replace(
            "+00:00", "Z")
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?created_before=%s' % date_string,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], str(registration1.id))

    def test_filter_registration_no_matches(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?registrant_id=test_id',
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_filter_registration_unknown_filter(self):
        # Setup
        registration1, registration2 = self.make_different_registrations()
        # Execute
        response = self.adminclient.get(
            '/api/v1/registrations/?something=test_id',
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)


class TestRegistrationHelpers(AuthenticatedAPITestCase):

    def test_get_risk_status(self):
        # prebirth, over 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-01", "2016-09-22"), "normal")
        # postbirth, over 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("postbirth", "1998-01-02", "2016-09-22"), "high")
        # prebirth, under 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-06", "2016-09-22"), "high")
        # prebirth, over 18, more than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-05", "2016-01-22"), "high")


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
                "edd": "2016-11-30",
            },
        }
        registration = Registration.objects.create(**registration_data)
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
        self.assertEqual(registration.data["invalid_fields"], [
            'Invalid UUID registrant_id', 'Language not a valid option',
            'Mother DOB invalid', 'Estimated Due Date invalid',
            'Operator ID invalid']
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
        self.assertEqual(registration.data["invalid_fields"], [
            'Language is missing from data', 'Mother DOB missing',
            'Estimated Due Date missing', 'Operator ID missing']
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
                "baby_dob": "2016-01-01"
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_pmtct_postbirth_malformed_data(self):
        """ Malformed data pmtct_postbirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother01",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01",
                "language": "en",
                "mom_dob": "199-01-27",
                "baby_dob": "2016-01-09"
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(registration.data["invalid_fields"], [
            'Invalid UUID registrant_id', 'Language not a valid option',
            'Mother DOB invalid', 'Baby Date of Birth cannot be in the future',
            'Operator ID invalid']
        )

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
        self.assertEqual(registration.data["invalid_fields"], [
            'Language is missing from data', 'Mother DOB missing',
            'Baby Date of Birth missing', 'Operator ID missing']
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
                "language": "eng_ZA"
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
                "language": "en"
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(registration.data["invalid_fields"], [
            'Invalid UUID registrant_id', 'Operator ID invalid',
            'MSISDN of Registrant invalid', 'MSISDN of device invalid',
            'Language not a valid option']
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
        self.assertEqual(registration.data["invalid_fields"], [
            'Facility (clinic) code missing', 'Operator ID missing',
            'MSISDN of Registrant missing', 'MSISDN of device missing',
            'Language is missing from data']
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
                "consent": True
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
                "consent": None
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(registration.data["invalid_fields"], [
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
            ]
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
                "consent": None
            },
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, False)
        registration.refresh_from_db()
        self.assertEqual(registration.data["invalid_fields"], [
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
            ]
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
        self.assertEqual(registration.data["invalid_fields"], [
            "Invalid UUID registrant_id",
            "Operator ID missing",
            "MSISDN of Registrant missing",
            "MSISDN of device missing",
            "Language is missing from data",
            "Consent is missing",
            "ID type missing",
            "Estimated Due Date missing",
            "Facility (clinic) code missing",
            ]
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
                "consent": True
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
        self.assertEqual(registration.data["invalid_fields"], [
            "Operator ID missing",
            "MSISDN of Registrant missing",
            "MSISDN of device missing",
            "Language is missing from data",
            "Consent is missing",
            "ID type missing",
        ])

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
                "consent": True
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
        self.assertEqual(registration.data["invalid_fields"], [
            "Operator ID missing",
            "MSISDN of Registrant missing",
            "MSISDN of device missing",
            "Language is missing from data",
            "Consent is missing",
        ])


class TestSubscriptionRequestCreation(AuthenticatedAPITestCase):

    @responses.activate
    def test_src_pmtct_prebirth_1(self):
        """ Test a prebirth registration before 30 weeks """
        # Setup
        # . setup pmtct_prebirth registration and set validated to true
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-05-01"  # in week 23 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 11)
        self.assertEqual(sr.next_sequence_number, 17)  # (23 - 6) * 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 111)

    @responses.activate
    def test_src_pmtct_prebirth_2(self):
        """ Test a prebirth registration 30 - 35 weeks """
        # Setup
        # . setup pmtct_prebirth registration and set validated to true
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-02-20"  # in week 33 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.2")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 12)
        self.assertEqual(sr.next_sequence_number, 6)  # (33 - 30) * 2
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 112)

    @responses.activate
    def test_src_pmtct_prebirth_3(self):
        """ Test a prebirth registration after 35 weeks """
        # Setup
        # . setup pmtct_prebirth registration and set validated to true
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-01-11"  # in week 39 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.3")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 13)
        self.assertEqual(sr.next_sequence_number, 12)  # (39 - 35) * 3
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 113)

    @responses.activate
    def test_src_pmtct_postbirth_1(self):
        """ Test a postbirth registration """
        # Setup
        # . setup pmtct_postbirth registration and set validated to true
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
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 14)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 114)

    @responses.activate
    def test_src_pmtct_postbirth_2(self):
        """ Test a postbirth registration """
        # Setup
        # . setup pmtct_postbirth registration and set validated to true
        registration_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "baby_dob": "2015-12-01"
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.2")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 15)
        self.assertEqual(sr.next_sequence_number, 3)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 115)

    @responses.activate
    def test_src_nurseconnect(self):
        """ Test a nurseconnect registration """
        # Setup
        # . setup nurseconnect registration and set validated to true
        registration_data = {
            "reg_type": "nurseconnect",
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821112222",
                "msisdn_device": "+27821112222",
                "faccode": "123456",
                "language": "eng_ZA"
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "nurse001-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 61)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 161)

    @responses.activate
    def test_src_momconnect_prebirth_clinic_1(self):
        """ Test a clinic prebirth registration before 30 weeks """
        # Setup
        # . setup momconnect_prebirth self registration, set validated to true
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
                "dob": "1982-08-01",
                "language": "eng_ZA",
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "faccode": "123456",
                "consent": True
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 21)
        self.assertEqual(sr.next_sequence_number, 37)  # ((23 - 4) * 2) - 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 121)

    @responses.activate
    def test_src_momconnect_prebirth_clinic_2(self):
        """ Test a clinic prebirth registration after 30 weeks """
        # Setup
        # . setup momconnect_prebirth other registration, set validated to true
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": {
                "operator_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821114444",
                "id_type": "passport",
                "passport_no": "ZA1234",
                "passport_origin": "bw",
                "language": "eng_ZA",
                "edd": "2016-03-01",  # in week 32 of pregnancy
                "faccode": "123456",
                "consent": True
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.2")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 22)
        self.assertEqual(sr.next_sequence_number, 4)  # ((32 - 30) * 3) - 2
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 122)

    @responses.activate
    def test_src_momconnect_prebirth_public(self):
        """ Test a public prebirth registration """
        # Setup
        # . setup momconnect_prebirth self registration, set validated to true
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "language": "eng_ZA",
                "consent": True
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 41)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 141)

    @responses.activate
    def test_src_momconnect_prebirth_chw(self):
        """ Test a chw prebirth registration """
        # Setup
        # . setup momconnect_prebirth other registration, set validated to true
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_partialuser(),
            "data": {
                "operator_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821114444",
                "id_type": "none",
                "mom_dob": "",
                "language": "eng_ZA",
                "consent": True
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_partial.1")
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 42)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 142)


class TestRegistrationCreation(AuthenticatedAPITestCase):

    @responses.activate
    def test_registration_process_good(self):
        """ Test a full registration process with good data """
        # Setup
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # . setup pmtct_prebirth registration
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": registrant_uuid,
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-05-01"  # in week 23 of pregnancy
            },
        }

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(registrant_uuid)
        utils_tests.mock_patch_identity(registrant_uuid)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check registration validated
        registration.refresh_from_db()
        self.assertEqual(registration.validated, True)

        # . check subscriptionrequest object
        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 11)
        self.assertEqual(sr.next_sequence_number, 17)  # (23 - 6) * 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 111)

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)

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
        self.assertEqual(registration.data["invalid_fields"],
                         ['Estimated Due Date missing'])

        # . check no subscriptionrequest objects were created
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)
