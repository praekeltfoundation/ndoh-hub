import datetime
import json
try:
    from unittest import mock
except ImportError:
    import mock
import pytz

from registrations.models import Registration
from registrations.serializers import RegistrationSerializer
from registrations.tests import AuthenticatedAPITestCase


class JembiAppRegistrationViewTests(AuthenticatedAPITestCase):
    def test_authentication_required(self):
        """
        Authentication must be provided in order to access the endpoint
        """
        response = self.client.post('/api/v1/jembiregistration/')
        self.assertEqual(response.status_code, 401)

    def test_invalid_request(self):
        """
        If the request is not valid, a 400 response with the offending fields
        should be returned
        """
        self.make_source_normaluser()
        response = self.normalclient.post('/api/v1/jembiregistration/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content)['mom_edd'],
            ["This field is required."])

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.delay')
    @mock.patch('ndoh_hub.utils.get_today')
    def test_successful_registration(self, today, task):
        """
        A successful validation should create a registration and fire off the
        async validation task
        """
        today.return_value = datetime.datetime(2016, 1, 1).date()
        source = self.make_source_normaluser()
        response = self.normalclient.post('/api/v1/jembiregistration/', {
            'external_id': 'test-external-id',
            'mom_edd': '2016-06-06',
            'mom_msisdn': '+27820000000',
            'mom_consent': True,
            'created': '2016-01-01 00:00:00',
            'hcw_msisdn': '+27821111111',
            'clinic_code': '123456',
            'mom_lang': 'eng_ZA',
            'mha': 1,
            'mom_dob': '1988-01-01',
            'mom_id_type': 'none',
        })

        self.assertEqual(response.status_code, 202)
        [reg] = Registration.objects.all()
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.created_at,
            datetime.datetime(2016, 1, 1, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEqual(reg.external_id, 'test-external-id')
        self.assertEqual(reg.created_by, self.normaluser)
        self.assertEqual(
            json.loads(response.content), RegistrationSerializer(reg).data)
        task.assert_called_once_with(registration_id=str(reg.pk))
