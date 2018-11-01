import json
import datetime
import uuid
from datetime import timedelta
from unittest import mock
from urllib.parse import urlparse

import requests
import responses
from django.contrib.auth.models import Group, User
from django.core import management
from django.core.cache import cache
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from django.utils import timezone
from requests_testadapter import TestAdapter, TestSession
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_hooks.models import model_saved

from ndoh_hub import utils, utils_tests

from .models import PositionTracker, Registration, Source, SubscriptionRequest
from .signals import psh_fire_created_metric, psh_validate_subscribe
from .tasks import (
    PushRegistrationToJembi,
    add_personally_identifiable_fields,
    get_risk_status,
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


class RecordingAdapter(TestAdapter):

    """ Record the request that was handled by the adapter.
    """

    def __init__(self, *args, **kwargs):
        self.requests = []
        super(RecordingAdapter, self).__init__(*args, **kwargs)

    def send(self, request, *args, **kw):
        self.requests.append(request)
        return super(RecordingAdapter, self).send(request, *args, **kw)


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
            "reg_type.authority.1",
        )

        # pmtct prebirth testing
        # week -1000 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", -1000),
            "pmtct_prebirth.authority.1",
        )
        # week 1 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 1),
            "pmtct_prebirth.authority.1",
        )
        # week 29 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 29),
            "pmtct_prebirth.authority.1",
        )
        # week 30 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 30),
            "pmtct_prebirth.authority.2",
        )
        # week 34 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 34),
            "pmtct_prebirth.authority.2",
        )
        # week 35 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 35),
            "pmtct_prebirth.authority.3",
        )
        # week 1000 prebirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_prebirth", "authority", 1000),
            "pmtct_prebirth.authority.3",
        )

        # pmtct postbirth testing
        # week -1000 postbirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_postbirth", "authority", -1000),
            "pmtct_postbirth.authority.1",
        )
        # week 0 postbirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_postbirth", "authority", 0),
            "pmtct_postbirth.authority.1",
        )
        # week 1 postbirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_postbirth", "authority", 1),
            "pmtct_postbirth.authority.1",
        )
        # week 2 postbirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_postbirth", "authority", 2),
            "pmtct_postbirth.authority.2",
        )
        # week 1000 postbirth
        self.assertEqual(
            utils.get_messageset_short_name("pmtct_postbirth", "authority", 1000),
            "pmtct_postbirth.authority.2",
        )

        # nurseconnect testing
        self.assertEqual(
            utils.get_messageset_short_name("nurseconnect", "authority", 500),
            "nurseconnect.authority.1",
        )

        # momconnect prebirth testing
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", -1000),
            "momconnect_prebirth.hw_full.1",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 0),
            "momconnect_prebirth.hw_full.1",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 30),
            "momconnect_prebirth.hw_full.1",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 31),
            "momconnect_prebirth.hw_full.2",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 35),
            "momconnect_prebirth.hw_full.2",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 36),
            "momconnect_prebirth.hw_full.3",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 37),
            "momconnect_prebirth.hw_full.4",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 38),
            "momconnect_prebirth.hw_full.5",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 39),
            "momconnect_prebirth.hw_full.6",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "hw_full", 1000),
            "momconnect_prebirth.hw_full.6",
        )

        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "authority", -1000),
            "momconnect_prebirth.authority.1",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "authority", 35),
            "momconnect_prebirth.authority.1",
        )
        self.assertEqual(
            utils.get_messageset_short_name("momconnect_prebirth", "authority", 1000),
            "momconnect_prebirth.authority.1",
        )

    def test_get_messageset_short_name_nurseconnect(self):
        """
        Should return the normal nurseconnect messageset by default, but should
        return the RTHB messageset if the flag is set
        """
        self.assertEqual(
            utils.get_messageset_short_name("nurseconnect", "hw_full", None),
            "nurseconnect.hw_full.1",
        )

        with self.settings(NURSECONNECT_RTHB=True):
            self.assertEqual(
                utils.get_messageset_short_name("nurseconnect", "hw_full", None),
                "nurseconnect_rthb.hw_full.1",
            )

    @responses.activate
    def test_get_messageset_schedule_sequence_nurseconnect_rthb(self):
        """
        If the messageset short_name is for nurseconnect RTHB, then the
        sequence number should be taken from the position tracker
        """
        # Normal nurseconnect subscription should always start at 1
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        self.assertEqual(
            utils.get_messageset_schedule_sequence("nurseconnect.hw_full.1", None),
            (61, 161, 1),
        )

        # RTHB nurseconnect should start according to the position tracker
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect_rthb.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        pt = PositionTracker.objects.get(label="nurseconnect_rthb")
        pt.position = 7
        pt.save()
        self.assertEqual(
            utils.get_messageset_schedule_sequence("nurseconnect_rthb.hw_full.1", None),
            (63, 163, 7),
        )
        pt.position = 10
        pt.save()
        self.assertEqual(
            utils.get_messageset_schedule_sequence("nurseconnect_rthb.hw_full.1", None),
            (63, 163, 10),
        )

    @responses.activate
    def test_get_messageset_schedule_sequence(self):
        # Setup all fixture responses
        # . pmtct
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.2"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.3"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.2"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . nurseconnect
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # . momconnect
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.2"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.3"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.4"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.5"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.6"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_partial.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # Check pmtct prebirth
        # . batch 1
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.1", 2),
            (11, 111, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.1", 7),
            (11, 111, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.1", 8),
            (11, 111, 2),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.1", 29),
            (11, 111, 23),
        )
        # . batch 2
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.2", 30),
            (12, 112, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.2", 31),
            (12, 112, 2),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.2", 32),
            (12, 112, 4),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.2", 34),
            (12, 112, 8),
        )
        # . batch 3
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.3", 35),
            (13, 113, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.3", 36),
            (13, 113, 3),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.3", 37),
            (13, 113, 6),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.3", 41),
            (13, 113, 18),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_prebirth.patient.3", 42),
            (13, 113, 20),
        )

        # Check pmtct postbirth
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_postbirth.patient.1", 0),
            (14, 114, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_postbirth.patient.1", 1),
            (14, 114, 3),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_postbirth.patient.2", 2),
            (15, 115, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_postbirth.patient.2", 3),
            (15, 115, 2),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("pmtct_postbirth.patient.2", 4),
            (15, 115, 3),
        )

        # Check nurseconnect
        self.assertEqual(
            utils.get_messageset_schedule_sequence("nurseconnect.hw_full.1", 500),
            (61, 161, 1),
        )

        # Check momconnect prebirth
        # . clinic
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.1", 0),
            (21, 121, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.1", 5),
            (21, 121, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.1", 6),
            (21, 121, 3),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.1", 30),
            (21, 121, 51),
        )

        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.2", 31),
            (22, 122, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.2", 32),
            (22, 122, 4),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.2", 35),
            (22, 122, 13),
        )

        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.3", 36),
            (23, 123, 1),
        )

        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.4", 37),
            (24, 124, 1),
        )

        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.5", 38),
            (25, 125, 1),
        )

        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.6", 39),
            (26, 126, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.hw_full.6", 42),
            (26, 126, 1),
        )

        # . public
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.patient.1", 0),
            (41, 141, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence("momconnect_prebirth.patient.1", 40),
            (41, 141, 1),
        )

        # . chw
        self.assertEqual(
            utils.get_messageset_schedule_sequence(
                "momconnect_prebirth.hw_partial.1", 0
            ),
            (42, 142, 1),
        )
        self.assertEqual(
            utils.get_messageset_schedule_sequence(
                "momconnect_prebirth.hw_partial.1", 40
            ),
            (42, 142, 1),
        )


class APITestCase(TestCase):
    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()
        self.partialclient = APIClient()
        self.otherclient = APIClient()
        self.session = TestSession()
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
    @responses.activate
    def test_create_third_party_registration_existing_identity(self):
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

    @responses.activate
    def test_create_third_party_registration_new_identity(self):
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

    @responses.activate
    def test_create_third_party_registration_no_swt_mha(self):
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


class TestRegistrationHelpers(AuthenticatedAPITestCase):
    def test_get_risk_status(self):
        # prebirth, over 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-01", "2016-09-22"), "normal"
        )
        # postbirth, over 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("postbirth", "1998-01-02", "2016-09-22"), "high"
        )
        # prebirth, under 18, less than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-06", "2016-09-22"), "high"
        )
        # prebirth, over 18, more than 20 weeks pregnant
        self.assertEqual(
            get_risk_status("prebirth", "1998-01-05", "2016-01-22"), "high"
        )


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
                "baby_dob": "2016-01-09",
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
                "Baby Date of Birth cannot be in the future",
                "Operator ID invalid",
            ],
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
                "edd": "2016-05-01",  # in week 23 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
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
                "edd": "2016-02-20",  # in week 33 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.2"
        )
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
                "edd": "2016-01-11",  # in week 39 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.3"
        )
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
                "baby_dob": "2016-01-01",
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.1"
        )
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
                "baby_dob": "2015-12-01",
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_postbirth.patient.2"
        )
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
                "language": "eng_ZA",
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1"
        )
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
    def test_src_whatsapp_nurseconnect(self):
        """ Test a whatsapp nurseconnect registration """
        # Setup
        # . setup whatsapp nurseconnect registration and set validated to true
        registration_data = {
            "reg_type": "whatsapp_nurseconnect",
            "registrant_id": "nurse001-63e2-4acc-9b94-26663b9bc267",
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
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_nurseconnect.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "nurse001-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 62)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 162)

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
                "mom_dob": "1982-08-01",
                "language": "eng_ZA",
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "faccode": "123456",
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1"
        )
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
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.2"
        )
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
    def test_src_whastapp_momconnect_prebirth_clinic_2(self):
        """ Test a whatsapp clinic prebirth registration after 30 weeks """
        # Setup
        # . setup momconnect_prebirth other registration, set validated to true
        registration_data = {
            "reg_type": "whatsapp_prebirth",
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
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_momconnect_prebirth.hw_full.2"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 94)
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
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
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
                "consent": True,
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_partial.1"
        )
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

    @responses.activate
    def test_src_whatsapp_pmtct_prebirth(self):
        """ Test a whatsapp pmtct prebirth registration before 30 weeks """
        # Setup
        # . setup pmtct_prebirth registration and set validated to true
        registration_data = {
            "reg_type": "whatsapp_pmtct_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": self.make_source_normaluser(),
            "data": {
                "operator_id": "mother01-63e2-4acc-9b94-26663b9bc267",
                "language": "eng_ZA",
                "mom_dob": "1999-01-27",
                "edd": "2016-05-01",  # in week 23 of pregnancy
            },
        }
        registration = Registration.objects.create(**registration_data)
        registration.validated = True
        registration.save()

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 92)
        self.assertEqual(sr.next_sequence_number, 17)  # (23 - 6) * 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 192)

    @responses.activate
    def test_src_whatsapp_pmtct_postbirth(self):
        """ Test a whatsapp pmtct postbirth registration """
        # Setup
        # . setup pmtct_postbirth registration and set validated to true
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
        registration.validated = True
        registration.save()

        # setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_pmtct_postbirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        # Execute
        cs = validate_subscribe.create_subscriptionrequests(registration)

        # Check
        self.assertEqual(cs, "SubscriptionRequest created")

        sr = SubscriptionRequest.objects.last()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 91)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 191)


class TestRegistrationCreation(AuthenticatedAPITestCase):
    @responses.activate
    def test_registration_process_pmtct_good(self):
        """ Test a full registration process with good data """
        # Setup
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821113333")
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        source = self.make_source_normaluser()
        source.name = "PMTCT USSD App"
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
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(registrant_uuid)
        utils_tests.mock_patch_identity(registrant_uuid)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check number of calls made:
        #   messageset, schedule, identity, patch identity, jembi registration
        #   identity, reverse identity, reverse identity, patch identity
        self.assertEqual(len(responses.calls), 9)

        # check jembi registration
        jembi_call = responses.calls[4]  # jembi should be the fifth one
        self.assertEqual(
            json.loads(jembi_call.request.body),
            {
                "lang": "en",
                "dob": "19990127",
                "cmsisdn": "+27821113333",
                "dmsisdn": "+27821113333",
                "faccode": "123456",
                "id": "8108015001051^^^ZAF^NI",
                "encdate": registration.created_at.strftime("%Y%m%d%H%M%S"),
                "type": 9,
                "swt": 1,
                "mha": 1,
                "risk_status": "high",
            },
        )
        self.assertEqual(
            jembi_call.request.url, "http://jembi/ws/rest/v1/pmtctSubscription"
        )
        self.assertEqual(jembi_call.request.method, "POST")

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
    def test_registration_process_pmtct_no_facility(self):
        """ Test a full registration process with good data """
        # Setup
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821113333")
        utils_tests.mock_get_messageset_by_shortname("popi.hw_full.1")
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        source = self.make_source_adminuser()
        source.name = "CLINIC USSD App"
        source.save()

        # Create linked momconnect registration
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
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
        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)

        Registration.objects.create(**registration_data)

        source = self.make_source_normaluser()
        source.name = "PMTCT USSD App"
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
            },
        }

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(
            registrant_uuid,
            {
                "addresses": {"msisdn": {"+8108015001051": {"default": True}}},
                "default_addr_type": "msisdn",
            },
        )
        utils_tests.mock_patch_identity(registrant_uuid)

        # Execute
        Registration.objects.create(**registration_data)

        # check jembi registration
        jembi_call = responses.calls[13]  # jembi should be the fourteenth one
        self.assertEqual(json.loads(jembi_call.request.body)["faccode"], "123456")

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_registration_process_pmtct_minimal_data(self):
        """ Test a full registration process with good data """
        # Setup
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        source = self.make_source_normaluser()
        source.name = "PMTCT USSD App"
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
                "faccode": "123456",
            },
        }

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(
            registrant_uuid,
            {
                "addresses": {"msisdn": {"+8108015001051": {"default": True}}},
                "default_addr_type": "msisdn",
            },
        )
        utils_tests.mock_patch_identity(registrant_uuid)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check number of calls made:
        #   messageset, schedule, identity, patch identity, jembi registration
        #   get identity, patch identity
        self.assertEqual(len(responses.calls), 8)

        # check jembi registration
        jembi_call = responses.calls[5]  # jembi should be the sixth one
        self.assertEqual(
            json.loads(jembi_call.request.body),
            {
                "lang": "en",
                "dob": "19990127",
                "cmsisdn": "+8108015001051",
                "dmsisdn": "+8108015001051",
                "faccode": "123456",
                "id": "8108015001051^^^ZAF^TEL",
                "encdate": registration.created_at.strftime("%Y%m%d%H%M%S"),
                "type": 9,
                "swt": 1,
                "mha": 1,
                "risk_status": "high",
            },
        )
        self.assertEqual(
            jembi_call.request.url, "http://jembi/ws/rest/v1/pmtctSubscription"
        )
        self.assertEqual(jembi_call.request.method, "POST")

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
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821113333")
        utils_tests.mock_get_messageset_by_shortname("popi.hw_full.1")
        # . reactivate post-save hook
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # NOTE: manually setting the name here so the mapping in the test
        #       works, better approach would be to make sure the names
        #       generated for sources in the tests match what's expected
        #       in production
        source = self.make_source_adminuser()
        source.name = "CLINIC USSD App"
        source.save()

        # . setup momconnect_prebirth self registration (clinic)
        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "source": source,
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

        # . setup fixture responses
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        # disabled service rating for now
        # utils_tests.mock_create_servicerating_invite(registrant_uuid)

        # Execute
        registration = Registration.objects.create(**registration_data)

        # Check
        # . check number of calls made:
        #   message set, schedule, popi message set, jembi registration,
        #   id_store mother, id_store mother_reverse,
        #   id_store registrant_rever, id_store patch
        self.assertEqual(len(responses.calls), 8)

        # . check registration validated
        registration.refresh_from_db()
        self.assertEqual(registration.validated, True)

        # . check subscriptionrequest object
        sr = SubscriptionRequest.objects.filter(messageset=21).first()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 21)
        self.assertEqual(sr.next_sequence_number, 37)  # ((23 - 4) * 2) - 1
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 121)

        # check popi subscription request object
        sr = SubscriptionRequest.objects.filter(messageset=71).first()
        self.assertEqual(sr.identity, "mother01-63e2-4acc-9b94-26663b9bc267")
        self.assertEqual(sr.messageset, 71)
        self.assertEqual(sr.next_sequence_number, 1)
        self.assertEqual(sr.lang, "eng_ZA")
        self.assertEqual(sr.schedule, 171)

        # Teardown
        post_save.disconnect(psh_validate_subscribe, sender=Registration)

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

    @responses.activate
    def test_push_registration_to_jembi(self):
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111", "lang": "en"},
        )
        utils_tests.mock_get_identity_by_msisdn("+27000000000")
        utils_tests.mock_get_identity_by_msisdn("+27111111111")

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username="testnormaluser"),
        )

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

        jembi_call = responses.calls[2]  # jembi should be the third one
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
        )

        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_push_registration_to_jembi_no_mom_dob(self):
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("39b073a1-68b5-44e6-9b6a-db4282085c36")
        utils_tests.mock_patch_identity("39b073a1-68b5-44e6-9b6a-db4282085c36")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27710967611", "lang": "en"},
        )
        utils_tests.mock_get_identity_by_msisdn("+27710967611")

        # Setup
        source = Source.objects.create(
            name="PUBLIC USSD App",
            authority="patient",
            user=User.objects.get(username="testnormaluser"),
        )

        registration_data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "39b073a1-68b5-44e6-9b6a-db4282085c36",
            "source": source,
            "data": {
                "operator_id": "39b073a1-68b5-44e6-9b6a-db4282085c36",
                "edd": "2017-09-03",
                "language": "eng_ZA",
                "consent": True,
                "msisdn_registrant": "+27710967611",
                "id_type": "sa_id",
                "faccode": "269833",
                "msisdn_device": "+27710967611",
                "sa_id_no": "7708050793083",
            },
        }

        registration = Registration.objects.create(**registration_data)
        self.assertFalse(registration.validated)
        registration.save()

        jembi_call = responses.calls[2]  # jembi should be the third one
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
        )

        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_push_external_chw_registration_to_jembi(self):
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_partial.1"
        )
        utils_tests.mock_get_messageset_by_shortname("popi.hw_partial.1")
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111", "lang": "en"},
        )
        utils_tests.mock_get_identity_by_msisdn("+27000000000")
        utils_tests.mock_get_identity_by_msisdn("+27111111111")

        # Setup
        source = Source.objects.create(
            name="EXTERNAL CHW App",
            authority="hw_partial",
            user=User.objects.get(username="testpartialuser"),
        )

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
        self.assertFalse(registration.validated)
        registration.save()

        jembi_call = responses.calls[3]  # jembi should be the fourth one
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
        )

        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_push_external_clinic_registration_to_jembi(self):
        post_save.connect(psh_validate_subscribe, sender=Registration)

        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.hw_full.1"
        )
        utils_tests.mock_get_messageset_by_shortname("popi.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_push_registration_to_jembi(
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={"cmsisdn": "+27111111111", "lang": "en"},
        )
        utils_tests.mock_get_identity_by_msisdn("+27000000000")
        utils_tests.mock_get_identity_by_msisdn("+27111111111")

        # Setup
        source = Source.objects.create(
            name="EXTERNAL Clinic App",
            authority="hw_full",
            user=User.objects.get(username="testadminuser"),
        )

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
                "edd": "2016-05-01",
                "faccode": "123456",
                "msisdn_device": "+27000000000",
                "msisdn_registrant": "+27111111111",
                "consent": True,
            },
        }

        registration = Registration.objects.create(**registration_data)
        self.assertFalse(registration.validated)
        registration.save()

        jembi_call = responses.calls[3]  # jembi should be the forth one
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
        )

        post_save.disconnect(psh_validate_subscribe, sender=Registration)

    @responses.activate
    def test_push_momconnect_registration_to_jembi_via_management_task(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "pmtct_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_msisdn("+2700000000")
        utils_tests.mock_get_identity_by_msisdn("+27111111111")
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
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        stdout = StringIO()
        call_command(
            "jembi_submit_registrations",
            "--since",
            format_timestamp(registration.created_at - timedelta(seconds=1)),
            "--until",
            format_timestamp(registration.created_at + timedelta(seconds=1)),
            stdout=stdout,
        )

        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 registrations.", str(registration.pk), "Done."]),
        )

        jembi_call = responses.calls[1]  # jembi should be the second request
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
        )

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

    @responses.activate
    def test_push_nurseconnect_registration_to_jembi_via_management_task(self):
        # Mock API call to SBM for message set
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "nurseconnect.hw_full.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_msisdn("+27821112222")
        utils_tests.mock_get_identity_by_id(
            "nurseconnect-identity",
            {"nurseconnect": {"persal_no": "persal", "sanc_reg_no": "sanc"}},
        )
        utils_tests.mock_patch_identity("nurseconnect-identity")
        utils_tests.mock_jembi_json_api_call(
            url="http://jembi/ws/rest/v1/nc/subscription",
            ok_response="jembi-is-ok",
            err_response="jembi-is-unhappy",
            fields={
                "cmsisdn": "+27821112222",
                "dmsisdn": "+27821112222",
                "persal": "persal",
                "sanc": "sanc",
            },
        )

        # Setup
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
        # NOTE: we're faking validation step here
        registration.validated = True
        registration.save()

        def format_timestamp(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")

        stdout = StringIO()
        call_command(
            "jembi_submit_registrations",
            "--source",
            str(source.pk),
            "--registration",
            registration.pk.hex,
            stdout=stdout,
        )

        self.assertEqual(
            stdout.getvalue().strip(),
            "\n".join(["Submitting 1 registrations.", str(registration.pk), "Done."]),
        )

        jembi_call = responses.calls[2]
        self.assertEqual(
            jembi_call.request.url, "http://jembi/ws/rest/v1/nc/subscription"
        )
        self.assertEqual(
            json.loads(jembi_call.response.text), {"result": "jembi-is-ok"}
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
        self.make_registration_for_jembi_helpdesk()

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
    def test_send_outgoing_message_to_jembi_nurseconnect(self):
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
        self.make_source_normaluser()

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
            "user_id": "unknown-uuid",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
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

    def test_send_outgoing_message_to_jembi_improperly_configured(self):
        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "unknown-uuid",
            "label": "Complaint",
        }
        # Execute
        with self.settings(JEMBI_BASE_URL=""):
            response = self.normalclient.post(
                "/api/v1/jembi/helpdesk/outgoing/", user_request
            )
            self.assertEqual(response.status_code, 503)

    @responses.activate
    def test_send_outgoing_message_to_jembi_error_response(self):
        self.make_registration_for_jembi_helpdesk()

        responses.add(
            responses.POST,
            "http://jembi/ws/rest/v1/helpdesk",
            status=500,
            content_type="application/json",
            body="This was a bad request.",
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
        }
        # Execute
        with self.assertRaises(requests.exceptions.HTTPError):
            response = self.normalclient.post(
                "/api/v1/jembi/helpdesk/outgoing/", user_request
            )
            self.assertEqual(response.status_code, 500)
            self.assertTrue("This was a bad request." in str(response.content))

    @responses.activate
    def test_send_outgoing_message_to_jembi_bad_data(self):
        self.make_registration_for_jembi_helpdesk()

        responses.add(
            responses.POST,
            "http://jembi/ws/rest/v1/helpdesk",
            status=400,
            content_type="application/json",
            body="This was a bad request.",
        )

        user_request = {
            "to": "+27123456789",
            "content": "this is a sample reponse",
            "reply_to": "this is a sample user message",
            "inbound_created_on": self.inbound_created_on_date,
            "outbound_created_on": self.outbound_created_on_date,
            "user_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "helpdesk_operator_id": 1234,
            "label": "Complaint",
        }

        with mock.patch("registrations.views.logger.warning") as mock_logger:
            response = self.normalclient.post(
                "/api/v1/jembi/helpdesk/outgoing/", user_request
            )
            self.assertEqual(response.status_code, 400)
            self.assertTrue("This was a bad request." in str(response.content))
        mock_logger.assert_called()

    @responses.activate
    def test_send_outgoing_message_to_jembi_with_blank_values(self):
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

    @responses.activate
    def test_send_outgoing_message_to_jembi_via_whatsapp(self):
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
        self.assertEqual(
            sorted(response.data["metrics_available"]),
            sorted(["registrations.created.sum"]),
        )

    @responses.activate
    def test_post_metrics(self):
        # Setup
        # deactivate Testsession for this test
        self.session = None
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


class TestMetrics(AuthenticatedAPITestCase):
    def setUp(self):
        responses.add(responses.POST, "http://metrics/api/v1/metrics/", json={})
        return super(TestMetrics, self).setUp()

    def _check_request(self, request, method, params=None, data=None, headers=None):
        self.assertEqual(request.method, method)
        if params is not None:
            url = urlparse.urlparse(request.url)
            qs = urlparse.parse_qsl(url.query)
            self.assertEqual(dict(qs), params)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)
        if data is None:
            self.assertEqual(request.body, None)
        else:
            self.assertEqual(json.loads(request.body), data)

    @responses.activate
    def test_direct_fire(self):
        # Execute
        result = utils.fire_metric.apply_async(
            kwargs={"metric_name": "foo.last", "metric_value": 1}
        )
        # Check
        [request] = responses.calls
        self._check_request(request.request, "POST", data={"foo.last": 1.0})
        self.assertEqual(result.get(), "Fired metric <foo.last> with value <1.0>")

    @responses.activate
    def test_created_metric(self):
        # reconnect metric post_save hook
        post_save.connect(
            psh_fire_created_metric,
            sender=Registration,
            dispatch_uid="psh_fire_created_metric",
        )

        # Execute
        self.make_registration_adminuser()
        self.make_registration_adminuser()

        # Check
        [request1, request3] = responses.calls
        self._check_request(
            request1.request, "POST", data={"registrations.created.sum": 1.0}
        )
        self._check_request(
            request3.request, "POST", data={"registrations.created.sum": 1.0}
        )

        # remove post_save hooks to prevent teardown errors
        post_save.disconnect(
            psh_fire_created_metric,
            sender=Registration,
            dispatch_uid="psh_fire_created_metric",
        )


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


class TestRevalidateRegistrationsCommand(AuthenticatedAPITestCase):
    @responses.activate
    @mock.patch("ndoh_hub.utils.get_today", return_value=override_get_today())
    def test_revalidate_registrations_info_not_removed(self, mock_today):
        # create a valid momconnect registration that was incorrectly marked
        # as invalid and the personal information has not yet been removed
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "consent": True,
                "msisdn_device": "+27821112222",
                "msisdn_registrant": "+27821112222",
                "edd": "2016-08-01",
                "mom_dob": "1982-08-01",
                "language": "eng_ZA",
                "operator_id": "operator-63e2-4acc-9b94-26663b9bc267",
                "test": "test",
                "invalid_fields": ["Estimated Due Date missing"],
            },
            "source": self.make_source_normaluser(),
            "validated": False,
        }
        check_registration = Registration.objects.create(**data)

        # Setup fixture responses
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821112222")
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_get_identity_by_id(registrant_uuid)
        utils_tests.mock_patch_identity(registrant_uuid)
        utils_tests.mock_get_active_subscriptions(registrant_uuid, count=0)

        stdout = StringIO()
        call_command(
            "revalidate_registrations",
            "--invalid-field",
            "Estimated Due Date missing",
            "--sbm-url",
            "http://sbm.org/api/v1/",
            "--sbm-token",
            "the_token",
            stdout=stdout,
        )

        check_registration.refresh_from_db()
        self.assertEqual(check_registration.validated, True)

        output = stdout.getvalue().strip().split("\n")

        self.assertEqual(len(output), 2)
        self.assertEqual(
            output[0], "Validating registration %s" % check_registration.id
        )
        self.assertEqual(output[1], "Successfully revalidated 1 registrations")

    @responses.activate
    @mock.patch("ndoh_hub.utils.get_today", return_value=override_get_today())
    def test_revalidate_registrations_info_removed(self, mock_today):
        # create a valid momconnect registration that was incorrectly marked
        # as invalid and the personal information has already been removed

        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "uuid_device": "mother01-63e2-4acc-9b94-26663b9bc267",
                "uuid_registrant": "mother01-63e2-4acc-9b94-26663b9bc267",
                "edd": "2016-08-01",
                "operator_id": "operator-63e2-4acc-9b94-26663b9bc267",
                "invalid_fields": ["Estimated Due Date missing"],
            },
            "source": self.make_source_normaluser(),
            "validated": False,
        }
        check_registration = Registration.objects.create(**data)

        # Setup fixture responses
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            details={"consent": True, "addresses": {"msisdn": {"+27821112222": {}}}},
        )
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821112222")
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_patch_identity(registrant_uuid)
        utils_tests.mock_get_active_subscriptions(registrant_uuid, count=0)

        stdout = StringIO()
        call_command(
            "revalidate_registrations",
            "--invalid-field",
            "Estimated Due Date missing",
            "--sbm-url",
            "http://sbm.org/api/v1/",
            "--sbm-token",
            "the_token",
            stdout=stdout,
        )

        check_registration.refresh_from_db()
        self.assertEqual(check_registration.validated, True)

        output = stdout.getvalue().strip().split("\n")

        self.assertEqual(len(output), 2)
        self.assertEqual(
            output[0], "Validating registration %s" % check_registration.id
        )
        self.assertEqual(output[1], "Successfully revalidated 1 registrations")

    @responses.activate
    @mock.patch("ndoh_hub.utils.get_today", return_value=override_get_today())
    def test_revalidate_registrations_in_batches(self, mock_today):
        # create 2 valid momconnect registrations that were incorrectly marked
        # as invalid
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "uuid_device": "mother01-63e2-4acc-9b94-26663b9bc267",
                "uuid_registrant": "mother01-63e2-4acc-9b94-26663b9bc267",
                "edd": "2016-08-01",
                "operator_id": "operator-63e2-4acc-9b94-26663b9bc267",
                "invalid_fields": ["Estimated Due Date missing"],
            },
            "source": self.make_source_normaluser(),
            "validated": False,
        }
        check_registration_1 = Registration.objects.create(**data)
        check_registration_2 = Registration.objects.create(**data)

        # Setup fixture responses
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"
        utils_tests.mock_get_identity_by_id(
            "mother01-63e2-4acc-9b94-26663b9bc267",
            details={"consent": True, "addresses": {"msisdn": {"+27821112222": {}}}},
        )
        utils_tests.mock_patch_identity("mother01-63e2-4acc-9b94-26663b9bc267")
        utils_tests.mock_get_identity_by_msisdn("+27821112222")
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "momconnect_prebirth.patient.1"
        )
        utils_tests.mock_get_schedule(schedule_id)
        utils_tests.mock_patch_identity(registrant_uuid)
        utils_tests.mock_get_active_subscriptions(registrant_uuid, count=0)

        # run command with batch-size 1
        stdout = StringIO()
        call_command(
            "revalidate_registrations",
            "--invalid-field",
            "Estimated Due Date missing",
            "--batch-size",
            "1",
            "--sbm-url",
            "http://sbm.org/api/v1/",
            "--sbm-token",
            "the_token",
            stdout=stdout,
        )

        # check only one registration validated
        check_registration_1.refresh_from_db()
        self.assertEqual(check_registration_1.validated, True)

        check_registration_2.refresh_from_db()
        self.assertEqual(check_registration_2.validated, False)

        # run command with batch-size 1
        call_command(
            "revalidate_registrations",
            "--invalid-field",
            "Estimated Due Date missing",
            "--batch-size",
            "1",
            "--sbm-url",
            "http://sbm.org/api/v1/",
            "--sbm-token",
            "the_token",
            stdout=stdout,
        )

        check_registration_2.refresh_from_db()
        self.assertEqual(check_registration_2.validated, True)

        output = stdout.getvalue().strip().split("\n")

        self.assertEqual(len(output), 4)
        self.assertEqual(
            output[0], "Validating registration %s" % check_registration_1.id
        )
        self.assertEqual(output[1], "Successfully revalidated 1 registrations")
        self.assertEqual(
            output[2], "Validating registration %s" % check_registration_2.id
        )
        self.assertEqual(output[3], "Successfully revalidated 1 registrations")

    @responses.activate
    def test_revalidate_registrations_with_sub(self):
        # create a valid momconnect registration that was incorrectly marked
        # as invalid
        data = {
            "reg_type": "momconnect_prebirth",
            "registrant_id": "mother01-63e2-4acc-9b94-26663b9bc267",
            "data": {
                "uuid_device": "mother01-63e2-4acc-9b94-26663b9bc267",
                "uuid_registrant": "mother01-63e2-4acc-9b94-26663b9bc267",
                "edd": "2016-08-01",
                "operator_id": "operator-63e2-4acc-9b94-26663b9bc267",
                "invalid_fields": ["Estimated Due Date missing"],
            },
            "source": self.make_source_normaluser(),
            "validated": False,
        }
        check_registration = Registration.objects.create(**data)
        registrant_uuid = "mother01-63e2-4acc-9b94-26663b9bc267"

        # When the identity has a sub the reg shouldn't be revalidated
        utils_tests.mock_get_active_subscriptions(registrant_uuid, count=1)

        stdout = StringIO()
        call_command(
            "revalidate_registrations",
            "--invalid-field",
            "Estimated Due Date missing",
            "--sbm-url",
            "http://sbm.org/api/v1/",
            "--sbm-token",
            "the_token",
            stdout=stdout,
        )

        check_registration.refresh_from_db()
        self.assertEqual(check_registration.validated, False)

        output = stdout.getvalue().strip().split("\n")

        self.assertEqual(len(output), 3)
        self.assertEqual(
            output[0], "Validating registration %s" % check_registration.id
        )
        self.assertEqual(
            output[1],
            "Identity %s already has subscription. Skipping." % registrant_uuid,
        )
        self.assertEqual(output[2], "Successfully revalidated 0 registrations")
