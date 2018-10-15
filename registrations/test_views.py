import datetime
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
import json
from unittest import mock

from registrations.models import Registration, PositionTracker
from registrations.serializers import RegistrationSerializer
from registrations.tests import AuthenticatedAPITestCase


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
