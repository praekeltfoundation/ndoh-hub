from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.test import TestCase
import json
from unittest import mock
from uuid import uuid4
import responses

from registrations.models import Registration, Source, SubscriptionRequest
from registrations.serializers import RegistrationSerializer
from registrations.signals import (
    psh_fire_created_metric, psh_validate_subscribe)
from registrations.tasks import (
    validate_subscribe_jembi_app_registration as task, validate_subscribe)
from ndoh_hub import utils_tests
from .tests import AuthenticatedAPITestCase


class ValidateSubscribeJembiAppRegistrationsTests(TestCase):
    def setUp(self):
        post_save.disconnect(
            receiver=psh_validate_subscribe, sender=Registration,
            dispatch_uid='psh_validate_subscribe')
        post_save.disconnect(
            receiver=psh_fire_created_metric, sender=Registration,
            dispatch_uid='psh_fire_created_metric')

    def tearDown(self):
        post_save.connect(psh_validate_subscribe, sender=Registration,
                          dispatch_uid='psh_validate_subscribe')
        post_save.connect(psh_fire_created_metric, sender=Registration,
                          dispatch_uid='psh_fire_created_metric')

    @responses.activate
    def test_get_or_update_identity_by_address_result(self):
        """
        If the get returns one or more identities, then the first identity
        should be used
        """
        responses.add(
            responses.GET,
            'http://is/api/v1/identities/search/'
            '?details__addresses__msisdn=%2B27820000000',
            json={
                'results': [
                    {'identity': 1},
                    {'identity': 2},
                ]
            }, status=200, match_querystring=True)

        r = task.get_or_update_identity_by_address('+27820000000')
        self.assertEqual(r, {'identity': 1})

    @responses.activate
    def test_get_or_update_identity_by_address_no_result(self):
        """
        If the get returns no result, then a new identity should be created
        """
        responses.add(
            responses.GET,
            'http://is/api/v1/identities/search/'
            '?details__addresses__msisdn=%2B27820000000',
            json={'results': []},
            status=200, match_querystring=True)

        responses.add(
            responses.POST, 'http://is/api/v1/identities/',
            json={'identity': 'result'})

        r = task.get_or_update_identity_by_address('+27820000000')
        self.assertEqual(r, {'identity': 'result'})
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'details': {
                'default_addr_type': 'msisdn',
                'addresses': {
                    'msisdn': {
                        '+27820000000': {'default': True},
                    },
                },
            },
        })

    @responses.activate
    def test_get_or_update_identity_by_address_not_primary(self):
        """
        If the identity returned by the identity store does not have the
        address we're looking for as the primary address, then it should not
        be returned.
        """
        responses.add(
            responses.GET,
            'http://is/api/v1/identities/search/'
            '?details__addresses__msisdn=%2B27820000000',
            json={
                'results': [
                    {
                        'details': {
                            'addresses': {
                                'msisdn': {
                                    '+27820000000': {},
                                    '+27820000001': {'default': True},
                                }
                            }
                        }
                    }
                ]
            }, status=200, match_querystring=True)

        responses.add(
            responses.POST, 'http://is/api/v1/identities/',
            json={'identity': 'result'})

        r = task.get_or_update_identity_by_address('+27820000000')
        self.assertEqual(r, {'identity': 'result'})

    def test_is_opted_out(self):
        """
        Return True if the address on the identity is opted out, and
        False if it isn't
        """
        identity = {
            'details': {
                'default_addr_type': 'msisdn',
                'addresses': {
                    'msisdn': {
                        '+27820000000': {},
                        '+27821111111': {'optedout': True},
                    },
                },
            },
        }

        self.assertFalse(task.is_opted_out(identity, '+27820000000'))
        self.assertTrue(task.is_opted_out(identity, '+27821111111'))

    @responses.activate
    def test_opt_in(self):
        """
        Creates a valid opt in
        """
        responses.add(responses.POST, 'http://is/api/v1/optin/')

        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        identity = {'id': 'test-identity-id'}
        task.opt_in(identity, '+27820000000', source)

        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'address': '+27820000000',
            'address_type': 'msisdn',
            'identity': 'test-identity-id',
            'request_source': 'testsource',
            'requestor_source_id': source.id,
        })

    @responses.activate
    @mock.patch('registrations.tasks.group_send')
    def test_send_webhook(self, websocket):
        """
        Sends a webhook to the specified URL with the registration status
        Also send the status over websocket
        """
        responses.add(responses.POST, 'http://test/callback')

        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'callback_url': 'http://test/callback',
                'callback_auth_token': 'test-token',
            }, created_by=user
        )

        task.send_webhook(reg)

        self.assertEqual(
            json.loads(responses.calls[-1].request.body), reg.status)
        self.assertEqual(
            responses.calls[-1].request.headers['Authorization'],
            'Bearer test-token')

        websocket.assert_called_once_with('user.{}'.format(user.id), {
            'type': 'registration.event',
            'data': reg.status,
        })

    @responses.activate
    @mock.patch('registrations.tasks.group_send')
    def test_send_webhook_no_url(self, websocket):
        """
        If no URL is specified, then the webhook should not be sent, but the
        websocket message should still be sent.
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={},
            created_by=user)

        task.send_webhook(reg)
        self.assertEqual(len(responses.calls), 0)

        websocket.assert_called_once_with('user.{}'.format(user.id), {
            'type': 'registration.event',
            'data': reg.status,
        })

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'send_webhook')
    def test_fail_validation(self, send_webhook):
        """
        Save the failed fields on the registration, and then send a webhook
        with the failed fields
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={})

        task.fail_validation(reg, {'test_field': "Test reason"})

        send_webhook.assert_called_once_with(reg)
        reg.refresh_from_db()
        self.assertEqual(reg.data['invalid_fields'], {
            'test_field': "Test reason"})

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'send_webhook')
    def test_fail_error(self, send_webhook):
        """
        Sends a webhook with details of error
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={})

        task.fail_error(reg, {'test_field': "Test reason"})

        send_webhook.assert_called_once_with(reg)
        self.assertEqual(reg.data['error_data'], {
            'test_field': "Test reason"})

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'send_webhook')
    def test_registration_success(self, send_webhook):
        """
        Sends a webhook with the successful registration
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={})

        task.registration_success(reg)

        send_webhook.assert_called_once_with(reg)

    @responses.activate
    def test_is_registered_on_whatsapp_true(self):
        """
        If the wassup API returns that the number is registered, should return
        True
        """
        def cb(request):
            data = json.loads(request.body)
            self.assertEqual(data, {
                "number": "+27820000000",
                "msisdns": ["+27821111111"],
                "wait": True,
            })
            return (200, {}, json.dumps([{
                "status": "valid",
                "wa_id": "27821111111"
            }]))

        responses.add_callback(
            responses.POST, 'http://wassup/',
            callback=cb, content_type='application/json')

        self.assertTrue(task.is_registered_on_whatsapp('+27821111111'))
        self.assertEqual(
            responses.calls[-1].request.headers['Authorization'],
            'Token wassup-token')

    @responses.activate
    def test_is_registered_on_whatsapp_false(self):
        """
        If the wassup API returns that the number is registered, should return
        False
        """
        def cb(request):
            data = json.loads(request.body)
            self.assertEqual(data, {
                "number": "+27820000000",
                "msisdns": ["+27821111111"],
                "wait": True,
            })
            return (200, {}, json.dumps([{
                "status": "invalid",
                "wa_id": "27821111111"
            }]))

        responses.add_callback(
            responses.POST, 'http://wassup/',
            callback=cb, content_type='application/json')
        self.assertFalse(task.is_registered_on_whatsapp('+27821111111'))
        self.assertEqual(
            responses.calls[-1].request.headers['Authorization'],
            'Token wassup-token')

    def test_create_pmtct_registration_whatsapp(self):
        """
        If the registration is a whatsapp registration, then the resulting
        PMTCT registration should also be for whatsapp
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='whatsapp_prebirth', source=source, data={
                'language': 'eng_ZA',
                'mom_dob': '1989-01-01',
                'edd': '2019-01-01',
            })
        operator = {'id': 'operator-id'}

        task.create_pmtct_registration(reg, operator)

        pmtct_reg = Registration.objects.order_by('created_at').last()
        self.assertEqual(pmtct_reg.reg_type, 'whatsapp_pmtct_prebirth')
        self.assertEqual(pmtct_reg.data, {
            'language': 'eng_ZA',
            'mom_dob': '1989-01-01',
            'edd': '2019-01-01',
            'operator_id': 'operator-id',
        })

    def test_create_pmtct_registration_sms(self):
        """
        If the registration is an sms registration, then the resulting
        PMTCT registration should also be for sms
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='momconnect_prebirth', source=source, data={
                'language': 'eng_ZA',
                'mom_dob': '1989-01-01',
                'edd': '2019-01-01',
            })
        operator = {'id': 'operator-id'}

        task.create_pmtct_registration(reg, operator)

        pmtct_reg = Registration.objects.order_by('created_at').last()
        self.assertEqual(pmtct_reg.reg_type, 'pmtct_prebirth')
        self.assertEqual(pmtct_reg.data, {
            'language': 'eng_ZA',
            'mom_dob': '1989-01-01',
            'edd': '2019-01-01',
            'operator_id': 'operator-id',
        })

    @responses.activate
    def test_is_identity_subscribed(self):
        """
        Returns true if any of the short names of the subcribed to messagesets
        match the supplied regex, else returns false
        """
        responses.add(
            responses.GET, 'http://sbm/api/v1/messageset/',
            json={
                'results': [
                    {
                        'id': 1,
                        'short_name': 'momconnect_prebirth.hw_full.1',
                    },
                ],
            })
        responses.add(
            responses.GET,
            'http://sbm/api/v1/subscriptions/?active=True&identity=test-id',
            json={
                'results': [
                    {'messageset': 1},
                ]
            }, match_querystring=True)

        self.assertTrue(
            task.is_identity_subscribed({'id': 'test-id'}, r'prebirth'))
        self.assertFalse(
            task.is_identity_subscribed({'id': 'test-id'}, r'foo'))

    @responses.activate
    def test_is_valid_clinic_code_true(self):
        """
        If there are results for the clinic code search, then True should be
        returned
        """
        responses.add(
            responses.GET,
            'http://jembi/ws/rest/v1/facilityCheck?criteria=code%3A123456',
            json={
                "title": "FacilityCheck",
                "headers": [
                    {
                        "name": "code",
                        "column": "code",
                        "type": "java.lang.String",
                        "hidden": False,
                        "meta": False
                    },
                    {
                        "name": "value",
                        "column": "value",
                        "type": "java.lang.String",
                        "hidden": False,
                        "meta": False
                    },
                    {
                        "name": "uid",
                        "column": "uid",
                        "type": "java.lang.String",
                        "hidden": False,
                        "meta": False
                    },
                    {
                        "name": "name",
                        "column": "name",
                        "type": "java.lang.String",
                        "hidden": False,
                        "meta": False
                    }
                ],
                "rows": [
                    [
                        "123456",
                        "123456",
                        "yGVQRg2PXNh",
                        "wc Test Clinic"
                    ]
                ],
                "width": 4,
                "height": 1
            },
            match_querystring=True)

        self.assertTrue(task.is_valid_clinic_code('123456'))

    @responses.activate
    def test_is_valid_clinic_code_false(self):
        """
        If there are no results for the clinic code search, then False should
        be returned
        """
        responses.add(
            responses.GET,
            'http://jembi/ws/rest/v1/facilityCheck?criteria=code%3A123456',
            json={
                "title": "FacilityCheck",
                "headers": [],
                "rows": [],
                "width": 0,
                "height": 0
            },
            match_querystring=True)

        self.assertFalse(task.is_valid_clinic_code('123456'))

    @responses.activate
    def test_send_welcome_message_whatsapp(self):
        """
        Should escape formatting for the USSD codes, and send using the correct
        channel
        """
        responses.add(responses.POST, 'http://ms/api/v1/outbound/')
        task.send_welcome_message(
            "eng_ZA", "WHATSAPP", "+27820001000", "identity-uuid")
        request = responses.calls[-1].request
        self.assertEqual(json.loads(request.body), {
            "to_addr": "+27820001000",
            "to_identity": "identity-uuid",
            "channel": "WHATSAPP",
            "content":
                "Welcome to MomConnect! For more services dial "
                "```*134*550*7#```, to stop dial ```*134*550*1#``` (Free). To "
                "move to WhatsApp, reply “WA”. Std SMS rates apply.",
        })

    @responses.activate
    def test_send_welcome_message_sms(self):
        """
        Should send the SMS text using the correct channel and language
        """
        responses.add(responses.POST, 'http://ms/api/v1/outbound/')
        task.send_welcome_message(
            "nso_ZA", "JUNE_TEXT", "+27820001000", "identity-uuid")
        request = responses.calls[-1].request
        self.assertEqual(json.loads(request.body), {
            "to_addr": "+27820001000",
            "to_identity": "identity-uuid",
            "channel": "JUNE_TEXT",
            "content":
                "O amogetšwe go MomConnect! Go hwetša ditirelo "
                "leletša*134*550*7#, go emiša letša*134*550*1# (Mahala)."
                "Go iša go WhatsApp, fetola WA. Go šoma ditefelo tša Std SMS."
        })

    @responses.activate
    def test_on_failure(self):
        """
        If there is a failure in processing the registration, then a webhook
        should be sent detailing the error
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
            })

        responses.add(
            responses.POST, 'http://testcallback/')

        self.assertRaises(KeyError, task.apply(args=(reg.pk,)).get)

        request = responses.calls[-1].request
        self.assertEqual(
            request.headers['Authorization'], 'Bearer test-auth-token')
        callback = json.loads(request.body)
        reg.refresh_from_db()
        self.assertEqual(callback, reg.status)

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    @responses.activate
    def test_already_subscribed(self, get_identity, is_subscribed):
        """
        If the registrant is already subscribed to a prebirth message set,
        then the registration should not go through, and there should be a
        failure callback.
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
            })

        responses.add(responses.POST, 'http://testcallback')

        get_identity.return_value = {
            'id': 'mother-id',
        }
        is_subscribed.return_value = True
        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'registration_id': str(reg.pk),
            'registration_data': RegistrationSerializer(reg).data,
            'status': 'validation_failed',
            'error': {
                'mom_msisdn':
                    'Number is already subscribed to MomConnect messaging',
            },
        })

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    @responses.activate
    def test_opted_out_no_opt_in(self, get_identity, is_subscribed, opted_out):
        """
        If the registrant has previously opted out, and they haven't selected
        to opt in again, then the registration should not go through, and
        there should be a failure callback.
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_opt_in': False,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
            })

        responses.add(responses.POST, 'http://testcallback')
        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'registration_id': str(reg.pk),
            'registration_data': RegistrationSerializer(reg).data,
            'status': 'validation_failed',
            'error': {
                'mom_opt_in':
                    'Mother has previously opted out and has not chosen to '
                    'opt back in again',
            },
        })

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'opt_in')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    def test_opted_out_with_opt_in(
            self, get_identity, is_subscribed, opted_out, optin, whatsapp):
        """
        If the registrant has previously opted out, and they have selected
        to opt in again, then it should opt them in again and continue
        the registration
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_opt_in': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
            })

        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = True
        whatsapp.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        optin.assert_called_once_with(
            {'id': 'mother-id'}, '+27820000000', source)

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_subscriptionrequests')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_valid_clinic_code')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    def test_whatsapp_registration(
            self, get_identity, is_subscribed, opted_out, whatsapp, clinic,
            fail):
        """
        If the registrant opted to receive messages on whatsapp, and they're
        registered on WhatsApp, then the resulting registration should be
        for whatsapp
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_whatsapp': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
                'faccode': '123456',
            })

        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = True
        clinic.return_value = True
        fail.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        reg.refresh_from_db()
        self.assertEqual(reg.reg_type, 'whatsapp_prebirth')
        self.assertEqual(reg.data['registered_on_whatsapp'], True)

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_subscriptionrequests')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_valid_clinic_code')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    def test_sms_registration(
            self, get_identity, is_subscribed, opted_out, whatsapp, clinic,
            fail):
        """
        If the registrant opted to receive messages on whatsapp, but they're
        not registered on WhatsApp, then the resulting registration should be
        for sms
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_whatsapp': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
                'faccode': '123456',
            })

        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True
        fail.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        reg.refresh_from_db()
        self.assertEqual(reg.reg_type, 'momconnect_prebirth')
        self.assertEqual(reg.data['registered_on_whatsapp'], False)

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_valid_clinic_code')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    @responses.activate
    def test_invalid_clinic_code(
            self, get_identity, is_subscribed, opted_out, whatsapp, clinic):
        """
        If the clinic code is invalid, then the registration should not
        validate, and an error webhook should be returned
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_whatsapp': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
                'faccode': '123456',
            })

        responses.add(responses.POST, 'http://testcallback/')
        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = False

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'registration_id': str(reg.pk),
            'registration_data': RegistrationSerializer(reg).data,
            'status': 'validation_failed',
            'error': {
                'clinic_code': 'Not a recognised clinic code',
            },
        })

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'send_welcome_message')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_subscriptionrequests')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_popi_subscriptionrequest')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_valid_clinic_code')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    @responses.activate
    def test_registration_complete_no_pmtct(
            self, get_identity, is_subscribed, opted_out, whatsapp, clinic,
            subreq, popi_subreq, welcome_msg):
        """
        Valid parameters should result in a successful registration and a
        success webhook being sent
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_whatsapp': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
                'faccode': '123456',
                'mom_pmtct': False,
                'language': "eng_ZA",
            })

        responses.add(responses.POST, 'http://testcallback/')
        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'registration_id': str(reg.pk),
            'registration_data': RegistrationSerializer(reg).data,
            'status': 'succeeded',
        })
        self.assertEqual(Registration.objects.count(), 1)

    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'send_welcome_message')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_pmtct_registration')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_subscriptionrequests')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'create_popi_subscriptionrequest')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_valid_clinic_code')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_registered_on_whatsapp')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_opted_out')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'is_identity_subscribed')
    @mock.patch(
        'registrations.tasks.validate_subscribe_jembi_app_registration.'
        'get_or_update_identity_by_address')
    @responses.activate
    def test_registration_complete_with_pmtct(
            self, get_identity, is_subscribed, opted_out, whatsapp, clinic,
            subreq, popi_subreq, pmtct, welcome_msg):
        """
        Valid parameters should result in a successful registration and a
        success webhook being sent.
        """
        user = User.objects.create_user('test', 'test@example.org', 'test')
        source = Source.objects.create(
            name='testsource', user=user, authority='hw_full')
        reg = Registration.objects.create(
            reg_type='jembi_momconnect', source=source, data={
                'msisdn_registrant': '+27820000000',
                'msisdn_device': '+27821111111',
                'mom_whatsapp': True,
                'callback_url': 'http://testcallback',
                'callback_auth_token': 'test-auth-token',
                'faccode': '123456',
                'mom_pmtct': True,
                'language': "eng_ZA",
            })

        responses.add(responses.POST, 'http://testcallback/')
        get_identity.return_value = {'id': 'mother-id'}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(json.loads(responses.calls[-1].request.body), {
            'registration_id': str(reg.pk),
            'registration_data': RegistrationSerializer(reg).data,
            'status': 'succeeded',
        })
        pmtct.assert_called_with(reg, {'id': "mother-id"})


class ServiceInfoSubscriptionRequestTestCase(AuthenticatedAPITestCase):
    def test_skips_other_registration_types(self):
        """
        Should skip creating subscription requests if not a whatsapp
        registration
        """
        registration = Registration(
            reg_type='momconnect_prebirth'
        )
        validate_subscribe.create_service_info_subscriptionrequest(
            registration)
        self.assertEqual(SubscriptionRequest.objects.count(), 0)

    @responses.activate
    def test_creates_subscriptionrequest(self):
        """
        Should create a subscription request at the correct place in the
        service info messages
        """
        registration = Registration(
            source=self.make_source_adminuser(),
            reg_type='whatsapp_prebirth',
            registrant_id=str(uuid4()),
            data={
                "edd": "2016-05-01",  # in week 23 of pregnancy
                "language": "zul_ZA",
            },
        )
        schedule_id = utils_tests.mock_get_messageset_by_shortname(
            "whatsapp_service_info.hw_full.1")
        utils_tests.mock_get_schedule(schedule_id)

        validate_subscribe.create_service_info_subscriptionrequest(
            registration)

        [subreq] = SubscriptionRequest.objects.all()
        self.assertEqual(subreq.identity, registration.registrant_id)
        self.assertEqual(subreq.messageset, 95)
        self.assertEqual(subreq.next_sequence_number, 5)
        self.assertEqual(subreq.lang, 'zul_ZA')
        self.assertEqual(subreq.schedule, schedule_id)
