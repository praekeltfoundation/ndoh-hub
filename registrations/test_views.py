import base64
import datetime
import hmac
import json
from hashlib import sha256
from unittest import mock
from urllib.parse import urlencode
from uuid import uuid4

import responses
from django.contrib.auth.models import Permission, User
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import dateparse, timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase

from changes.models import Change
from registrations.models import PositionTracker, Registration, Source
from registrations.serializers import RegistrationSerializer
from registrations.tests import AuthenticatedAPITestCase
from registrations.views import EngageContextView


class JembiAppRegistrationViewTests(AuthenticatedAPITestCase):
    def test_authentication_required(self):
        """
        Authentication must be provided in order to access the endpoint
        """
        response = self.client.post("/api/v1/jembiregistration/")
        self.assertEqual(response.status_code, 401)

    def test_invalid_request(self):
        """
        If the request is not valid, a 400 response with the offending fields
        should be returned
        """
        self.make_source_normaluser()
        response = self.normalclient.post("/api/v1/jembiregistration/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["mom_edd"], ["This field is required."]
        )

    @mock.patch("rest_framework.validators.UniqueValidator.__call__")
    def test_duplicate_external_id(self, validator):
        """
        If the external_id already exists, a 400 response with a appropriate
        message should be returned. This tests for a race condition where the
        serializer passes on two or more requests but the second one fails on
        the db.
        """

        source = self.make_source_normaluser()
        Registration.objects.create(
            external_id="test-external-id",
            reg_type="jembi_momconnect",
            registrant_id=None,
            data={},
            source=source,
            created_by=User.objects.get(username="testnormaluser"),
        )

        response = self.normalclient.post(
            "/api/v1/jembiregistration/",
            {
                "external_id": "test-external-id",
                "mom_edd": "2016-06-06",
                "mom_msisdn": "+27820000000",
                "mom_consent": True,
                "created": "2016-01-01 00:00:00",
                "hcw_msisdn": "+27821111111",
                "clinic_code": "123456",
                "mom_lang": "eng_ZA",
                "mha": 1,
                "mom_dob": "1988-01-01",
                "mom_id_type": "none",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)["external_id"], ["This field must be unique."]
        )

    @mock.patch("registrations.tasks.validate_subscribe_jembi_app_registration.delay")
    @mock.patch("ndoh_hub.utils.get_today")
    def test_successful_registration(self, today, task):
        """
        A successful validation should create a registration and fire off the
        async validation task
        """
        today.return_value = datetime.datetime(2016, 1, 1).date()
        source = self.make_source_normaluser()
        response = self.normalclient.post(
            "/api/v1/jembiregistration/",
            {
                "external_id": "test-external-id",
                "mom_edd": "2016-06-06",
                "mom_msisdn": "+27820000000",
                "mom_consent": True,
                "created": "2016-01-01 00:00:00",
                "hcw_msisdn": "+27821111111",
                "clinic_code": "123456",
                "mom_lang": "eng_ZA",
                "mha": 1,
                "mom_dob": "1988-01-01",
                "mom_id_type": "none",
            },
        )

        self.assertEqual(response.status_code, 202)
        [reg] = Registration.objects.all()
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.created_at, datetime.datetime(2016, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(reg.external_id, "test-external-id")
        self.assertEqual(reg.created_by, self.normaluser)
        self.assertEqual(json.loads(response.content), RegistrationSerializer(reg).data)
        task.assert_called_once_with(registration_id=str(reg.pk))


class JembiAppRegistrationStatusViewTests(AuthenticatedAPITestCase):
    def test_authentication_required(self):
        """
        Authentication must be provided in order to access the endpoint
        """
        response = self.client.get("/api/v1/jembiregistration/test-id/")
        self.assertEqual(response.status_code, 401)

    def test_invalid_id(self):
        """
        If a registration with a matching ID cannot be found, then a 404 should
        be returned
        """
        response = self.normalclient.get("/api/v1/jembiregistration/test-id/")
        self.assertEqual(response.status_code, 404)

    def test_get_registration_by_interal_external_id(self):
        """
        The status of the registration should be able to be fetched by both
        the internal and external ID
        """
        reg = Registration.objects.create(
            external_id="test-external",
            source=self.make_source_normaluser(),
            created_by=self.normaluser,
            data={},
        )

        response = self.normalclient.get(
            "/api/v1/jembiregistration/{}/".format(reg.external_id)
        )
        self.assertEqual(response.status_code, 200)

        response = self.normalclient.get("/api/v1/jembiregistration/{}/".format(reg.id))
        self.assertEqual(response.status_code, 200)

    def test_get_registration_only_by_user(self):
        """
        If the user who is fetching the registration is not the user that
        created the registration, then they should be denied permission to
        view that registration's status
        """
        reg = Registration.objects.create(
            source=self.make_source_normaluser(), created_by=self.adminuser
        )

        response = self.normalclient.get("/api/v1/jembiregistration/{}/".format(reg.id))
        self.assertEqual(response.status_code, 403)


class PositionTrackerViewsetTests(AuthenticatedAPITestCase):
    def test_authentication_required(self):
        """
        Authentication must be provided in order to access the endpoint
        """
        url = reverse("positiontracker-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        response = self.normalclient.get(url)
        self.assertEqual(response.status_code, 200)

    def test_permission_required(self):
        """
        The user must have the required permission to be able to perform the
        requested action
        """
        url = reverse("positiontracker-list")
        response = self.normalclient.post(url, data={"label": "test"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PositionTracker.objects.count(), 1)

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can add position tracker")
        )

        response = self.normalclient.post(url, data={"label": "test"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PositionTracker.objects.count(), 2)

    def test_increment_position_permission_required(self):
        """
        In order to increment the position on a position tracker, the user
        needs to have the increment position permission
        """
        pt = PositionTracker.objects.create(label="test", position=1)
        # Ensure that it's older than 12 hours
        [h] = pt.history.all()
        h.history_date -= datetime.timedelta(hours=13)
        h.save()

        url = reverse("positiontracker-increment-position", args=[str(pt.pk)])
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, 403)
        pt.refresh_from_db()
        self.assertEqual(pt.position, 1)

        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can increment the position")
        )

        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, 200)
        pt.refresh_from_db()
        self.assertEqual(pt.position, 2)

    def test_can_only_increment_once_every_12_hours(self):
        """
        In order to avoid retries HTTP requests incrementing the position more
        than once, and increment may only be allowed once every 12 hours
        """
        pt = PositionTracker.objects.create(label="test", position=1)
        # Ensure that it's older than 12 hours
        [h] = pt.history.all()
        h.history_date -= datetime.timedelta(hours=13)
        h.save()
        self.normaluser.user_permissions.add(
            Permission.objects.get(name="Can increment the position")
        )

        url = reverse("positiontracker-increment-position", args=[str(pt.pk)])
        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, 200)
        pt.refresh_from_db()
        self.assertEqual(pt.position, 2)

        response = self.normalclient.post(url)
        self.assertEqual(response.status_code, 400)
        pt.refresh_from_db()
        self.assertEqual(pt.position, 2)


class EngageContextViewTests(APITestCase):
    def add_authorization_token(self):
        """
        Adds credentials to the current client
        """
        user = User.objects.create_user("test")
        Source.objects.create(user=user)
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token {}".format(token.key))

    def add_identity_lookup_by_address_fixture(
        self, msisdn="+27820001001", identity_uuid=None, details=None
    ):
        """
        Adds the fixtures for the identity lookup. If details aren't specified, then
        an empty result is returned.
        """
        if identity_uuid is None and details is None:
            results = []
        else:
            details["addresses"] = {"msisdn": {msisdn: {"default": True}}}
            results = [{"id": identity_uuid, "details": details}]
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": msisdn})
            ),
            json={"results": results},
            status=200,
        )

    def add_subscription_lookup(self, identity_uuid, subscriptions=None):
        if subscriptions is None:
            subscriptions = []
        else:
            subscriptions = [
                {"id": i, "messageset_label": l} for i, l in enumerate(subscriptions)
            ]

        responses.add(
            responses.GET,
            "http://sbm/api/v1/subscriptions/?{}".format(
                urlencode({"identity": identity_uuid, "active": True})
            ),
            json={"results": subscriptions},
            status=200,
        )

    def assertDateTime(self, date):
        try:
            result = dateparse.parse_datetime(date)
            assert result is not None, "{} is an invalid date".format(date)
        except ValueError:
            self.fail("{} is an invalid date".format(date))

    def generate_hmac_signature(self, data, key):
        data = JSONRenderer().render(data)
        h = hmac.new(key.encode(), data, sha256)
        return base64.b64encode(h.digest()).decode()

    def test_get_identity_no_msisdn(self):
        """
        If no msisdn is presented, then no request for the identity should be made.
        """
        self.assertIsNone(EngageContextView().get_identity(None))

    @responses.activate
    def test_get_identity_no_results(self):
        """
        If there are no results for the specifed MSISDN, then None should be returned
        """
        self.add_identity_lookup_by_address_fixture(msisdn="+27820001001")
        self.assertIsNone(EngageContextView().get_identity(msisdn="+27820001001"))

    def get_registrations_no_identity(self):
        """
        If there is no identity given, then an empty list should be returned
        """
        self.assertEqual(EngageContextView().get_registrations(None), [])

    def test_authentication_required(self):
        """
        A valid token is required to access the API
        """
        url = reverse("engage-context")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_signature_required(self):
        """
        A valid signature is required on the request to access the API
        """
        self.add_authorization_token()
        url = reverse("engage-context")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn(
            "X-Engage-Hook-Signature header required", response.json()["detail"]
        )

        response = self.client.post(
            url, {}, format="json", HTTP_X_ENGAGE_HOOK_SIGNATURE="bad"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid hook signature", response.json()["detail"])

    @override_settings(ENGAGE_CONTEXT_HMAC_SECRET="hmac-secret")
    def test_returns_handshake(self):
        """
        Returns the handhshake info when the handshake key is found
        """
        self.add_authorization_token()
        data = {"handshake": True}
        url = reverse("engage-context")
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "capabilities": {
                    "actions": True,
                    "context_objects": [
                        {
                            "title": "Mother's Details",
                            "code": "mother_details",
                            "icon": "info-circle",
                            "type": "table",
                        },
                        {
                            "title": "Subscriptions",
                            "code": "subscriptions",
                            "icon": "profile",
                            "type": "ordered-list",
                        },
                    ],
                }
            },
        )

    @override_settings(ENGAGE_CONTEXT_HMAC_SECRET="hmac-secret")
    def test_returns_no_information(self):
        """
        Returns no information when there are no inbound messages
        """
        self.add_authorization_token()
        data = {"mother_details": {}, "subscriptions": []}
        url = reverse("engage-context")
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"version": "1.0.0-alpha", "context_objects": data, "actions": {}},
        )

    @responses.activate
    @override_settings(ENGAGE_CONTEXT_HMAC_SECRET="hmac-secret")
    def test_returns_information(self):
        """
        If the request has inbound messages, return the information for that user.
        """
        self.add_authorization_token()
        self.add_identity_lookup_by_address_fixture(
            msisdn="+27820001001",
            identity_uuid="mother-uuid",
            details={"mom_dob": "1980-08-08"},
        )
        self.add_subscription_lookup(
            identity_uuid="mother-uuid",
            subscriptions=["MomConnect Pregnancy WhatsApp", "Service Info WhatsApp"],
        )
        user = User.objects.create_user("test2")
        source = Source.objects.create(user=user)
        Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id="mother-uuid",
            data={"faccode": "123456", "edd": "2018-12-15"},
            source=source,
        )

        url = reverse("engage-context")
        data = {"messages": [{"from": "27820001001"}]}
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = response.json()
        context_objects = response.pop("context_objects")
        actions = response.pop("actions")
        self.assertEqual(response, {"version": "1.0.0-alpha"})

        self.assertEqual(
            context_objects["mother_details"],
            {
                "Facility Code": "123456",
                "Registration Type": "MomConnect pregnancy registration",
                "Date of Birth": "1980-08-08",
                "Expected Due Date": "2018-12-15",
            },
        )

        self.assertEqual(
            context_objects["subscriptions"],
            ["MomConnect Pregnancy WhatsApp", "Service Info WhatsApp"],
        )

        self.assertEqual(
            actions,
            {
                "baby_switch": {
                    "description": "Switch to baby messaging",
                    "url": "/api/v1/engage/action",
                    "payload": {
                        "registrant_id": "mother-uuid",
                        "action": "baby_switch",
                        "data": {},
                    },
                }
            },
        )

    @responses.activate
    @override_settings(ENGAGE_CONTEXT_HMAC_SECRET="hmac-secret")
    def test_no_baby_action_on_postbirth(self):
        """
        The switch to baby actions should only display when on pregnant messaging
        """
        mother_uuid = str(uuid4())
        self.add_authorization_token()
        self.add_identity_lookup_by_address_fixture(
            msisdn="+27820001001",
            identity_uuid=mother_uuid,
            details={"mom_dob": "1980-08-08"},
        )
        self.add_subscription_lookup(
            identity_uuid=mother_uuid,
            subscriptions=["MomConnect Baby WhatsApp", "Service Info WhatsApp"],
        )
        user = User.objects.create_user("test2")
        source = Source.objects.create(user=user)
        Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id=mother_uuid,
            data={"faccode": "123456", "edd": "2018-12-15"},
            source=source,
        )

        url = reverse("engage-context")
        data = {"messages": [{"from": "27820001001"}]}
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["actions"].get("baby_switch"), None)

    @responses.activate
    @override_settings(ENGAGE_CONTEXT_HMAC_SECRET="hmac-secret")
    def test_baby_action(self):
        """
        Making a POST request with the returned body should create a valid baby switch
        """
        mother_uuid = str(uuid4())
        self.add_authorization_token()
        self.add_identity_lookup_by_address_fixture(
            msisdn="+27820001001",
            identity_uuid=mother_uuid,
            details={"mom_dob": "1980-08-08"},
        )
        self.add_subscription_lookup(
            identity_uuid=mother_uuid,
            subscriptions=["MomConnect Pregnancy WhatsApp", "Service Info WhatsApp"],
        )
        user = User.objects.create_user("test2")
        source = Source.objects.create(user=user)
        Registration.objects.create(
            reg_type="momconnect_prebirth",
            registrant_id=mother_uuid,
            data={"faccode": "123456", "edd": "2018-12-15"},
            source=source,
        )

        url = reverse("engage-context")
        data = {"messages": [{"from": "27820001001"}]}
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        action = response.json()["actions"]["baby_switch"]
        data = {"address": "+27820001001", "payload": action["payload"]}
        response = self.client.post(
            action["url"],
            data,
            format="json",
            HTTP_X_ENGAGE_HOOK_SIGNATURE=self.generate_hmac_signature(
                data, "hmac-secret"
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [change] = Change.objects.all()
        self.assertEqual(change.registrant_id, mother_uuid)
        self.assertEqual(change.action, "baby_switch")
        self.assertTrue(change.validated)
