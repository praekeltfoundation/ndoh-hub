import json
import uuid
import datetime
from datetime import timedelta
import responses
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_hooks.models import model_saved

from .models import Source, Registration, SubscriptionRequest
from .signals import psh_validate_subscribe
from .tasks import validate_subscribe, get_risk_status
from ndoh_hub import utils, utils_tests


# Valid data for registrations
DATA_CLINIC_PREBIRTH = {
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
}
DATA_PUBLIC_PREBIRTH = {
    "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
    "msisdn_registrant": "+27821113333",
    "msisdn_device": "+27821113333",
    "language": "zul_ZA",
    "consent": True
}
DATA_PMTCT_PREBIRTH = {
    "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
    "language": "eng_ZA",
    "mom_dob": "1999-01-27",
    "edd": "2016-11-30",
}
DATA_PMTCT_POSTBIRTH = {
    "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
    "language": "eng_ZA",
    "mom_dob": "1999-01-27",
    "baby_dob": "2016-01-01"
}


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

    def make_external_source_limited(self):
        data = {
            "name": "test_source_external_limited",
            "authority": "hw_limited",
            "user": User.objects.get(username='testpartialuser')
        }
        return Source.objects.create(**data)

    def make_external_source_full(self):
        data = {
            "name": "test_source_external_full",
            "authority": "hw_full",
            "user": User.objects.get(username='testadminuser')
        }
        return Source.objects.create(**data)

    def make_registration_adminuser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_CLINIC_PREBIRTH,
            "source": self.make_source_adminuser()
        }
        return Registration.objects.create(**data)

    def make_registration_normaluser(self):
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_PUBLIC_PREBIRTH,
            "source": self.make_source_normaluser()
        }
        return Registration.objects.create(**data)

    def make_different_registrations(self):
        registration1_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": DATA_PMTCT_PREBIRTH,
            "validated": True
        }
        registration1 = Registration.objects.create(**registration1_data)
        registration2_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother02-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": DATA_PMTCT_POSTBIRTH,
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
            "data": DATA_CLINIC_PREBIRTH
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
        self.assertEqual(d.validated, True)
        self.assertEqual(d.data, DATA_CLINIC_PREBIRTH)
        self.assertEqual(d.created_by, self.adminuser)

    def test_create_registration_normaluser(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_PUBLIC_PREBIRTH
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
        self.assertEqual(d.validated, True)
        self.assertEqual(d.data, DATA_PUBLIC_PREBIRTH)
        self.assertEqual(d.created_by, self.normaluser)

    def test_create_registration_set_readonly_field(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_PUBLIC_PREBIRTH,
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
        self.assertEqual(d.validated, True)  # Should ignore True post_data
        self.assertEqual(d.data, DATA_PUBLIC_PREBIRTH)

    def test_create_registration_normaluser_invalid_reg_type(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_PUBLIC_PREBIRTH
        }
        # Execute
        response = self.normalclient.post('/api/v1/registration/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["reg_type"],
                         ['"momconnect" is not a valid choice.'])

    def test_create_registration_normaluser_invalid_data_fields(self):
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "operator_id": "baduuid",
                "msisdn_registrant": "+2782",
                "msisdn_device": "+2782",
                "language": "zulu",
                "consent": "no"
            }
        }
        # Execute
        response = self.normalclient.post('/api/v1/registration/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"], [
            'Invalid UUID: operator_id',
            'Invalid MSISDN: msisdn_registrant',
            'Invalid MSISDN: msisdn_device',
            'Invalid Language: language',
            'Invalid Consent: consent must be True'
        ])

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
        self.assertEqual(response.data["count"], 2)
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


@override_settings(
    IDENTITY_STORE_URL='http://identitystore/',
    IDENTITY_STORE_TOKEN='identitystore_token'
)
class TestThirdPartyRegistrationAPI(AuthenticatedAPITestCase):

    @responses.activate
    def test_create_third_party_registration_existing_identity(self):
        # Setup
        self.make_external_source_limited()

        responses.add(
            responses.GET,
            'http://identitystore/identities/search/?details__addresses__msisdn=%2B27831111111',  # noqa
            json={
                'count': 1,
                'next': None,
                'previous': None,
                'results': [{
                    'created_at': '2015-10-14T07:25:53.218988Z',
                    'created_by': 53,
                    'details': {
                        'addresses': {
                            'msisdn': {'+27831111111': {'default': True}}
                        },
                        'default_addr_type': 'msisdn',
                    },
                    'id': '3a4af5d9-887b-410f-afa1-460d4b3ecc05',
                    'operator': None,
                    'updated_at': '2016-10-27T19:04:03.138598Z',
                    'updated_by': 53,
                    'version': 1
                }]},
            match_querystring=True,
            status=200,
            content_type='application/json')
        responses.add(
            responses.GET,
            'http://identitystore/identities/search/?details__addresses__msisdn=%2B27824440000',  # noqa
            json={
                'count': 1,
                'next': None,
                'previous': None,
                'results': [{
                    'communicate_through': None,
                    'created_at': '2015-10-14T07:25:53.218988Z',
                    'created_by': 53,
                    'details': {
                        'addresses': {
                            'msisdn': {'+27824440000': {'default': True}}
                        },
                        'consent': False,
                        'default_addr_type': 'msisdn',
                        'lang_code': 'eng_ZA',
                        'last_mc_reg_on': 'clinic',
                        'mom_dob': '1999-02-21',
                        'sa_id_no': '27625249986',
                        'source': 'clinic'
                    },
                    'id': '02144938-847d-4d2c-9daf-707cb864d077',
                    'operator': '3a4af5d9-887b-410f-afa1-460d4b3ecc05',
                    'updated_at': '2016-10-27T19:04:03.138598Z',
                    'updated_by': 53,
                    'version': 1
            }]},
            match_querystring=True,
            status=200,
            content_type='application/json')
        responses.add(
            responses.PATCH,
            'http://identitystore/identities/02144938-847d-4d2c-9daf-707cb864d077/',  # noqa
            json={
                'count': 1,
                'next': None,
                'previous': None,
                'results': [{
                    'communicate_through': None,
                    'created_at': '2015-10-14T07:25:53.218988Z',
                    'created_by': 53,
                    'details': {
                        'addresses': {
                            'msisdn': {'+27824440000': {'default': True}}
                        },
                        'consent': False,
                        'default_addr_type': 'msisdn',
                        'lang_code': 'eng_ZA',
                        'last_mc_reg_on': 'clinic',
                        'mom_dob': '1999-02-21',
                        'sa_id_no': '27625249986',
                        'source': 'clinic'
                    },
                    'id': '02144938-847d-4d2c-9daf-707cb864d077',
                    'operator': '3a4af5d9-887b-410f-afa1-460d4b3ecc05',
                    'updated_at': '2016-10-27T19:04:03.138598Z',
                    'updated_by': 53,
                    'version': 1
            }]},
            match_querystring=True,
            status=200,
            content_type='application/json')
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
            "swt": 3
        }
        # Execute
        response = self.partialclient.post('/api/v1/extregistration/',
                                           json.dumps(post_data),
                                           content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, 'test_source_external_limited')
        self.assertEqual(d.reg_type, 'momconnect_prebirth')
        self.assertEqual(d.registrant_id,
                         "02144938-847d-4d2c-9daf-707cb864d077")
        self.assertEqual(d.data['edd'], '2016-11-05')

    @responses.activate
    def test_create_third_party_registration_new_identity(self):
        # Setup
        self.make_external_source_limited()

        responses.add(
            responses.GET,
            'http://identitystore/identities/search/?details__addresses__msisdn=%2B27831111111',  # noqa
            json={
                'count': 1,
                'next': None,
                'previous': None,
                'results': [{
                    'created_at': '2015-10-14T07:25:53.218988Z',
                    'created_by': 53,
                    'details': {
                        'addresses': {
                            'msisdn': {'+27831111111': {'default': True}}
                        },
                        'default_addr_type': 'msisdn',
                    },
                    'id': '3a4af5d9-887b-410f-afa1-460d4b3ecc05',
                    'operator': None,
                    'updated_at': '2016-10-27T19:04:03.138598Z',
                    'updated_by': 53,
                    'version': 1
            }]},
            match_querystring=True,
            status=200,
            content_type='application/json')
        responses.add(
            responses.GET,
            'http://identitystore/identities/search/?details__addresses__msisdn=%2B27824440000',  # noqa
            json={
                'count': 0,
                'next': None,
                'previous': None,
                'results': []
            },
            match_querystring=True,
            status=200,
            content_type='application/json')
        responses.add(
            responses.POST,
            'http://identitystore/identities/',
            json={
                'communicate_through': None,
                'created_at': '2015-10-14T07:25:53.218988Z',
                'created_by': 53,
                'details': {
                    'addresses': {
                        'msisdn': {'+27824440000': {'default': True}}
                    },
                    'consent': False,
                    'default_addr_type': 'msisdn',
                    'lang_code': 'eng_ZA',
                    'last_mc_reg_on': 'clinic',
                    'mom_dob': '1999-02-21',
                    'sa_id_no': '27625249986',
                    'source': 'clinic'
                },
                'id': '02144938-847d-4d2c-9daf-707cb864d077',
                'operator': '3a4af5d9-887b-410f-afa1-460d4b3ecc05',
                'updated_at': '2016-10-27T19:04:03.138598Z',
                'updated_by': 53,
                'version': 1
            },
            match_querystring=True,
            status=200,
            content_type='application/json')
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
            "swt": 3
        }
        # Execute
        response = self.partialclient.post('/api/v1/extregistration/',
                                           json.dumps(post_data),
                                           content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.source.name, 'test_source_external_limited')
        self.assertEqual(d.reg_type, 'momconnect_prebirth')
        self.assertEqual(d.registrant_id,
                         "02144938-847d-4d2c-9daf-707cb864d077")
        self.assertEqual(d.data['edd'], '2016-11-05')


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
            "data": DATA_PMTCT_PREBIRTH,
        }
        registration = Registration.objects.create(**registration_data)
        # Execute
        v = validate_subscribe.validate(registration)
        # Check
        self.assertEqual(v, True)

    def test_validate_pmtct_prebirth_extra_field(self):
        """ Malformed data pmtct_prebirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": DATA_PMTCT_PREBIRTH.copy(),
        }
        registration_data["data"]["foo"] = "bar"
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str(['Superfluous fields: foo']),
            str(cm.exception)
        )

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
                "foo": "bar"
            },
        }
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Invalid UUID: operator_id',
                'Invalid date: mom_dob',
                'Invalid date: edd',
                'Invalid Language: language']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Missing field: operator_id',
                'Missing field: mom_dob',
                'Missing field: edd',
                'Missing field: language']),
            str(cm.exception)
        )

    def test_validate_pmtct_postbirth_good(self):
        """ Good minimal data pmtct_postbirth test """
        # Setup
        registration_data = {
            "reg_type": "pmtct_postbirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": DATA_PMTCT_POSTBIRTH,
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Invalid UUID: operator_id',
                'Invalid date: mom_dob',
                'Invalid date: baby_dob is in the future',
                'Invalid Language: language']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Missing field: operator_id',
                'Missing field: mom_dob',
                'Missing field: baby_dob',
                'Missing field: language']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Invalid UUID: operator_id',
                'Invalid MSISDN: msisdn_registrant',
                'Invalid MSISDN: msisdn_device',
                'Invalid Language: language']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Missing field: operator_id',
                'Missing field: msisdn_registrant',
                'Missing field: msisdn_device',
                'Missing field: language',
                'Missing field: faccode']),
            str(cm.exception)
        )

    def test_validate_momconnect_prebirth_clinic_good(self):
        """ clinic momconnect_prebirth sa_id """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_adminuser(),
            "data": DATA_CLINIC_PREBIRTH,
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Invalid UUID: operator_id',
                'Invalid MSISDN: msisdn_registrant',
                'Invalid MSISDN: msisdn_device',
                'Invalid SA ID number: sa_id_no',
                'Invalid date: mom_dob',
                'Invalid Language: language',
                'Invalid date: edd',
                'Invalid Clinic Code: faccode',
                'Invalid Consent: consent must be True']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Invalid UUID: operator_id',
                'Invalid MSISDN: msisdn_registrant',
                'Invalid MSISDN: msisdn_device',
                'Missing field: passport_no',
                'Invalid Passport origin: passport_origin',
                'Invalid Language: language',
                'Invalid date: edd',
                'Invalid Clinic Code: faccode',
                'Invalid Consent: consent must be True']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Invalid UUID: registrant_id',
                'Missing field: operator_id',
                'Missing field: msisdn_registrant',
                'Missing field: msisdn_device',
                'Missing field: id_type',
                'Missing field: language',
                'Missing field: edd',
                'Missing field: faccode',
                'Missing field: consent']),
            str(cm.exception)
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Missing field: operator_id',
                'Missing field: msisdn_registrant',
                'Missing field: msisdn_device',
                'Missing field: id_type',
                'Missing field: language',
                'Missing field: consent']),
            str(cm.exception)
        )

    def test_validate_momconnect_prebirth_public_good(self):
        """ public momconnect_prebirth """
        # Setup
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": DATA_PUBLIC_PREBIRTH,
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
        # Execute
        with self.assertRaises(ValidationError) as cm:
            Registration.objects.create(**registration_data)
        # Check
        self.assertEqual(
            str([
                'Missing field: operator_id',
                'Missing field: msisdn_registrant',
                'Missing field: msisdn_device',
                'Missing field: language',
                'Missing field: consent']),
            str(cm.exception)
        )


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
            "data": DATA_PMTCT_POSTBIRTH,
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
            "data": DATA_CLINIC_PREBIRTH,
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
                "mom_dob": "1982-08-01",
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
    @patch('registrations.tasks.PushRegistrationToJembi.get_today')
    def test_registration_process_pmtct_good(self, mock_date):
        """ Test a full registration process with good data """
        # Setup
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        source = self.make_source_normaluser()
        source.name = 'PMTCT USSD App'
        source.save()

        # . setup pmtct_prebirth registration
        registration_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": registrant_uuid,
            "source": source,
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "msisdn_registrant": "+27821113333",
                "msisdn_device": "+27821113333",
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "faccode": "123456",
            },
        }

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1")
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(registrant_uuid)
        utils_tests.mock_patch_identity(registrant_uuid)
        mock_date.return_value = datetime.date(2016, 1, 1)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check number of calls made:
        #   messageset, schedule, identity, patch identity, jembi registration
        self.assertEqual(len(responses.calls), 5)

        # check jembi registration
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'lang': 'en',
            'dob': '19990127',
            'cmsisdn': '+27821113333',
            'dmsisdn': '+27821113333',
            'faccode': '123456',
            'id': '8108015001051^^^ZAF^NI',
            'encdate': '20160101000000',
            'type': 8,
            'swt': 1,
            'mha': 1,
        })

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
    def test_registration_process_clinic_good(self):
        """ Test a full registration process with good data """
        # Setup
        # registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # NOTE: manually setting the name here so the mapping in the test
        #       works, better approach would be to make sure the names
        #       generated for sources in the tests match what's expected
        #       in production
        source = self.make_source_adminuser()
        source.name = 'CLINIC USSD App'
        source.save()

        # . setup momconnect_prebirth self registration (clinic)
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
            "data": DATA_CLINIC_PREBIRTH,
        }

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)
        # disabled service rating for now
        # utils_tests.mock_create_servicerating_invite(registrant_uuid)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check number of calls made:
        #   message set, schedule, service rating, jembi registration
        self.assertEqual(len(responses.calls), 3)

        # . check registration validated
        registration.refresh_from_db()
        self.assertEqual(registration.validated, True)

        # . check subscriptionrequest object
        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 21)
        self.assertEqual(sr.next_sequence_number, 37)  # ((23 - 4) * 2) - 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 121)

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_registration_process_bad(self):
        """ Test a full registration process with bad data """
        # Setup
        self.make_source_normaluser()
        post_data = {
            "reg_type": "pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": DATA_PMTCT_PREBIRTH.copy()
        }
        del post_data["data"]["edd"]
        # Execute
        response = self.normalclient.post('/api/v1/registration/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"],
                         ['Missing field: edd'])
        # . check number of calls made
        self.assertEqual(len(responses.calls), 0)
        # . check no subscriptionrequest objects were created
        self.assertEqual(SubscriptionRequest.objects.all().count(), 0)

    @responses.activate
    def test_push_registration_to_jembi(self):
        post_save.connect(
            psh_validate_subscribe, sender=Registration)

        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            'momconnect_prebirth.patient.1')
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity(
            "mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={
                "cmsisdn": "+27111111111",
                "lang": "en",
            })

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username='testnormaluser'))

        registration_data = {
            "reg_type": "momconnect_prebirth",
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
                "msisdn_device": "+27000000000",
                "msisdn_registrant": "+27111111111",
                "consent": True,
            },
        }

        registration = Registration.objects.create(**registration_data)
        self.assertFalse(registration.validated)
        registration.save()

        jembi_call = responses.calls[-1]  # jembi should be the last one
        self.assertEqual(json.loads(jembi_call.response.text), {
            "result": "jembi-is-ok"
        })

        post_save.disconnect(
            psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_push_momconnect_registration_to_jembi_via_management_task(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            'pmtct_prebirth.patient.1')
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity(
            "mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111"})

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username='testnormaluser'))

        registration_data = {
            "reg_type": "momconnect_prebirth",
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

        def format_timestamp(ts):
            return ts.strftime('%Y-%m-%d %H:%M:%S')

        stdout = StringIO()
        call_command(
            'jembi_submit_registrations',
            '--since', format_timestamp(
                registration.created_at - timedelta(seconds=1)),
            '--until', format_timestamp(
                registration.created_at + timedelta(seconds=1)),
            stdout=stdout)

        self.assertEqual(stdout.getvalue().strip(), '\n'.join([
            'Submitting 1 registrations.',
            str(registration.pk,),
            'Done.',
        ]))

        [jembi_call] = responses.calls  # jembi should be the only one
        self.assertEqual(json.loads(jembi_call.response.text), {
            "result": "jembi-is-ok"
        })

    @responses.activate
    def test_push_nurseconnect_registration_to_jembi_via_management_task(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            'nurseconnect.hw_full.1')
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(
            "nurseconnect-identity", {
                'nurseconnect': {
                    'persal_no': 'persal',
                    'sanc_reg_no': 'sanc',
                }
            })
        utils_tests.mock_patch_identity(
            "nurseconnect-identity")
        utils_tests.mock_jembi_json_api_call(
            url='http://jembi/ws/rest/v1/nc/subscription',
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "persal": "persal",
                "sanc": "sanc",
            })

        # Setup
        source = Source.objects.create(
            name="NURSE USSD App",
            authority="hw_full",
            user=User.objects.get(username='testadminuser'))

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
        # NOTE: we're faking validation step here
        registration.validated = True
        registration.save()

        def format_timestamp(ts):
            return ts.strftime('%Y-%m-%d %H:%M:%S')

        stdout = StringIO()
        call_command(
            'jembi_submit_registrations',
            '--source', str(source.pk),
            '--registration', registration.pk.hex,
            stdout=stdout)

        self.assertEqual(stdout.getvalue().strip(), '\n'.join([
            'Submitting 1 registrations.',
            str(registration.pk,),
            'Done.',
        ]))

        [identity_store_call, jembi_call] = responses.calls
        self.assertEqual(
            jembi_call.request.url,
            'http://jembi/ws/rest/v1/nc/subscription')
        self.assertEqual(json.loads(jembi_call.response.text), {
            "result": "jembi-is-ok"
        })


class TestJembiHelpdeskOutgoing(AuthenticatedAPITestCase):

    def make_registration_for_jembi_helpdesk(self):
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
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
                "consent": True
            },
        }
        return Registration.objects.create(**registration_data)

    @responses.activate
    def test_send_outgoing_message_to_jembi(self):
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_jembi_json_api_call(
            url='http://jembi/ws/rest/v1/helpdesk',
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={})

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "this is a sample user message",
            "created_on": override_get_today(),
            "user_id": 'mother01-63e2-4acc-9b94-26663b9bc267',
            "label": 'Complaint'}
        # Execute
        response = self.normalclient.post(
            '/api/v1/jembi/helpdesk/outgoing/', user_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json['dmsisdn'], '+27123456789')
        self.assertEqual(request_json['cmsisdn'], '+27123456789')
        self.assertEqual(request_json['encdate'], '20160101000000')
        self.assertEqual(request_json['repdate'], '20160101000000')
        self.assertEqual(request_json['mha'], 1)
        self.assertEqual(request_json['swt'], 2)
        self.assertEqual(request_json['faccode'], '123456')
        self.assertEqual(request_json['data'], {
            'question': u'this is a sample user message',
            'answer': u'this is a sample response'})
        self.assertEqual(request_json['class'], 'Complaint')
        self.assertEqual(request_json['type'], 7)
        self.assertEqual(request_json['op'], 'operator-123456')

    def test_send_outgoing_message_to_jembi_invalid_user_id(self):
        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "created_on": override_get_today(),
            "user_id": 'unknown-uuid',
            "label": 'Complaint'}
        # Execute
        response = self.normalclient.post(
            '/api/v1/jembi/helpdesk/outgoing/', user_request)
        self.assertEqual(response.status_code, 404)

    def test_send_outgoing_message_to_jembi_improperly_configured(self):
        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "created_on": override_get_today(),
            "user_id": 'unknown-uuid',
            "label": 'Complaint'}
        # Execute
        with self.settings(JEMBI_BASE_URL=''):
            response = self.normalclient.post(
                '/api/v1/jembi/helpdesk/outgoing/', user_request)
            self.assertEqual(response.status_code, 503)

    @responses.activate
    def test_send_outgoing_message_to_jembi_bad_response(self):
        self.make_registration_for_jembi_helpdesk()

        responses.add(
            responses.POST,
            'http://jembi/ws/rest/v1/helpdesk',
            status=500, content_type='application/json'
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "created_on": override_get_today(),
            "user_id": 'mother01-63e2-4acc-9b94-26663b9bc267',
            "label": 'Complaint'}
        # Execute
        response = self.normalclient.post(
            '/api/v1/jembi/helpdesk/outgoing/', user_request)
        self.assertEqual(response.status_code, 400)

    @responses.activate
    def test_send_outgoing_message_to_jembi_with_blank_values(self):
        self.make_registration_for_jembi_helpdesk()

        utils_tests.mock_jembi_json_api_call(
            url='http://jembi/ws/rest/v1/helpdesk',
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={})

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample response",
            "reply_to": "",
            "created_on": override_get_today(),
            "user_id": 'mother01-63e2-4acc-9b94-26663b9bc267',
            "label": ""}
        # Execute
        response = self.normalclient.post(
            '/api/v1/jembi/helpdesk/outgoing/', user_request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(responses.calls), 1)
        request_json = json.loads(responses.calls[0].request.body)

        self.assertEqual(request_json['dmsisdn'], '+27123456789')
        self.assertEqual(request_json['cmsisdn'], '+27123456789')
        self.assertEqual(request_json['encdate'], '20160101000000')
        self.assertEqual(request_json['repdate'], '20160101000000')
        self.assertEqual(request_json['mha'], 1)
        self.assertEqual(request_json['swt'], 2)
        self.assertEqual(request_json['faccode'], '123456')
        self.assertEqual(request_json['data'], {
            'answer': u'this is a sample response',
            'question': ''})
        self.assertEqual(request_json['class'], '')
        self.assertEqual(request_json['type'], 7)
        self.assertEqual(request_json['op'], 'operator-123456')
