import json
from unittest import mock
from urllib.parse import urlencode
from uuid import uuid4

import responses
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.test import TestCase

from ndoh_hub import utils_tests
from registrations.models import (
    ClinicCode,
    Registration,
    Source,
    SubscriptionRequest,
    WhatsAppContact,
)
from registrations.serializers import RegistrationSerializer
from registrations.signals import psh_validate_subscribe
from registrations.tasks import (
    _create_rapidpro_clinic_registration,
    _create_rapidpro_public_registration,
    create_rapidpro_clinic_registration,
    create_rapidpro_public_registration,
    get_or_create_identity_from_msisdn,
    get_whatsapp_contact,
    opt_in_identity,
    send_welcome_message,
    update_identity_from_rapidpro_clinic_registration,
    update_identity_from_rapidpro_public_registration,
    validate_subscribe,
)
from registrations.tasks import validate_subscribe_jembi_app_registration as task

from .tests import AuthenticatedAPITestCase, override_get_today


class ValidateSubscribeJembiAppRegistrationsTests(TestCase):
    def setUp(self):
        post_save.disconnect(
            receiver=psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )

    def tearDown(self):
        post_save.connect(
            psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )

    @responses.activate
    def test_get_or_update_identity_by_address_result(self):
        """
        If the get returns one or more identities, then the first identity
        should be used
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/"
            "?details__addresses__msisdn=%2B27820000000",
            json={"results": [{"identity": 1}, {"identity": 2}]},
            status=200,
            match_querystring=True,
        )

        r = task.get_or_update_identity_by_address("+27820000000")
        self.assertEqual(r, {"identity": 1})

    @responses.activate
    def test_get_or_update_identity_by_address_no_result(self):
        """
        If the get returns no result, then a new identity should be created
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/"
            "?details__addresses__msisdn=%2B27820000000",
            json={"results": []},
            status=200,
            match_querystring=True,
        )

        responses.add(
            responses.POST, "http://is/api/v1/identities/", json={"identity": "result"}
        )

        r = task.get_or_update_identity_by_address("+27820000000")
        self.assertEqual(r, {"identity": "result"})
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "details": {
                    "default_addr_type": "msisdn",
                    "addresses": {"msisdn": {"+27820000000": {"default": True}}},
                }
            },
        )

    @responses.activate
    def test_get_or_update_identity_by_address_not_primary(self):
        """
        If the identity returned by the identity store does not have the
        address we're looking for as the primary address, then it should not
        be returned.
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/"
            "?details__addresses__msisdn=%2B27820000000",
            json={
                "results": [
                    {
                        "details": {
                            "addresses": {
                                "msisdn": {
                                    "+27820000000": {},
                                    "+27820000001": {"default": True},
                                }
                            }
                        }
                    }
                ]
            },
            status=200,
            match_querystring=True,
        )

        responses.add(
            responses.POST, "http://is/api/v1/identities/", json={"identity": "result"}
        )

        r = task.get_or_update_identity_by_address("+27820000000")
        self.assertEqual(r, {"identity": "result"})

    def test_is_opted_out(self):
        """
        Return True if the address on the identity is opted out, and
        False if it isn't
        """
        identity = {
            "details": {
                "default_addr_type": "msisdn",
                "addresses": {
                    "msisdn": {"+27820000000": {}, "+27821111111": {"optedout": True}}
                },
            }
        }

        self.assertFalse(task.is_opted_out(identity, "+27820000000"))
        self.assertTrue(task.is_opted_out(identity, "+27821111111"))

    @responses.activate
    def test_opt_in(self):
        """
        Creates a valid opt in
        """
        responses.add(responses.POST, "http://is/api/v1/optin/")

        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        identity = {"id": "test-identity-id"}
        task.opt_in(identity, "+27820000000", source)

        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "address": "+27820000000",
                "address_type": "msisdn",
                "identity": "test-identity-id",
                "request_source": "testsource",
                "requestor_source_id": source.id,
            },
        )

    @responses.activate
    def test_send_webhook(self):
        """
        Sends a webhook to the specified URL with the registration status
        Also send the status over websocket
        """
        responses.add(responses.POST, "http://test/callback")

        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "callback_url": "http://test/callback",
                "callback_auth_token": "test-token",
            },
            created_by=user,
        )

        task.send_webhook(reg)
        self.assertEqual(json.loads(responses.calls[-1].request.body), reg.status)
        self.assertEqual(
            responses.calls[-1].request.headers["Authorization"], "Bearer test-token"
        )

    @responses.activate
    def test_send_webhook_no_url(self):
        """
        If no URL is specified, then the webhook should not be sent, but the
        websocket message should still be sent.
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect", source=source, data={}, created_by=user
        )

        task.send_webhook(reg)
        self.assertEqual(len(responses.calls), 0)

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "send_webhook"
    )
    def test_fail_validation(self, send_webhook):
        """
        Save the failed fields on the registration, and then send a webhook
        with the failed fields
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect", source=source, data={}
        )

        task.fail_validation(reg, {"test_field": "Test reason"})

        send_webhook.assert_called_once_with(reg)
        reg.refresh_from_db()
        self.assertEqual(reg.data["invalid_fields"], {"test_field": "Test reason"})

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "send_webhook"
    )
    def test_fail_error(self, send_webhook):
        """
        Sends a webhook with details of error
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect", source=source, data={}
        )

        task.fail_error(reg, {"test_field": "Test reason"})

        send_webhook.assert_called_once_with(reg)
        self.assertEqual(reg.data["error_data"], {"test_field": "Test reason"})

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "send_webhook"
    )
    def test_registration_success(self, send_webhook):
        """
        Sends a webhook with the successful registration
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect", source=source, data={}
        )

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
            self.assertEqual(data, {"blocking": "wait", "contacts": ["+27821111112"]})
            return (
                200,
                {},
                json.dumps(
                    {
                        "contacts": [
                            {
                                "input": "+27821111112",
                                "status": "valid",
                                "wa_id": "27821111112",
                            }
                        ]
                    }
                ),
            )

        responses.add_callback(
            responses.POST,
            "http://engage/v1/contacts",
            callback=cb,
            content_type="application/json",
        )

        self.assertTrue(task.is_registered_on_whatsapp("+27821111112"))
        self.assertEqual(
            responses.calls[-1].request.headers["Authorization"], "Bearer engage-token"
        )

    @responses.activate
    def test_is_registered_on_whatsapp_false(self):
        """
        If the wassup API returns that the number is registered, should return
        False
        """

        def cb(request):
            data = json.loads(request.body)
            self.assertEqual(data, {"blocking": "wait", "contacts": ["+27821111111"]})
            return (
                200,
                {},
                json.dumps(
                    {"contacts": [{"input": "+27821111111", "status": "invalid"}]}
                ),
            )

        responses.add_callback(
            responses.POST,
            "http://engage/v1/contacts",
            callback=cb,
            content_type="application/json",
        )
        self.assertFalse(task.is_registered_on_whatsapp("+27821111111"))
        self.assertEqual(
            responses.calls[-1].request.headers["Authorization"], "Bearer engage-token"
        )

    def test_create_pmtct_registration_whatsapp(self):
        """
        If the registration is a whatsapp registration, then the resulting
        PMTCT registration should also be for whatsapp
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="whatsapp_prebirth",
            source=source,
            data={"language": "eng_ZA", "mom_dob": "1989-01-01", "edd": "2019-01-01"},
        )
        operator = {"id": "operator-id"}

        task.create_pmtct_registration(reg, operator)

        pmtct_reg = Registration.objects.order_by("created_at").last()
        self.assertEqual(pmtct_reg.reg_type, "whatsapp_pmtct_prebirth")
        self.assertEqual(
            pmtct_reg.data,
            {
                "language": "eng_ZA",
                "mom_dob": "1989-01-01",
                "edd": "2019-01-01",
                "operator_id": "operator-id",
            },
        )

    def test_create_pmtct_registration_sms(self):
        """
        If the registration is an sms registration, then the resulting
        PMTCT registration should also be for sms
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="momconnect_prebirth",
            source=source,
            data={"language": "eng_ZA", "mom_dob": "1989-01-01", "edd": "2019-01-01"},
        )
        operator = {"id": "operator-id"}

        task.create_pmtct_registration(reg, operator)

        pmtct_reg = Registration.objects.order_by("created_at").last()
        self.assertEqual(pmtct_reg.reg_type, "pmtct_prebirth")
        self.assertEqual(
            pmtct_reg.data,
            {
                "language": "eng_ZA",
                "mom_dob": "1989-01-01",
                "edd": "2019-01-01",
                "operator_id": "operator-id",
            },
        )

    @responses.activate
    def test_is_identity_subscribed(self):
        """
        Returns true if any of the short names of the subcribed to messagesets
        match the supplied regex, else returns false
        """
        responses.add(
            responses.GET,
            "http://sbm/api/v1/messageset/",
            json={
                "results": [{"id": 1, "short_name": "momconnect_prebirth.hw_full.1"}]
            },
        )
        responses.add(
            responses.GET,
            "http://sbm/api/v1/subscriptions/?active=True&identity=test-id",
            json={"results": [{"messageset": 1}]},
            match_querystring=True,
        )

        self.assertTrue(task.is_identity_subscribed({"id": "test-id"}, r"prebirth"))
        self.assertFalse(task.is_identity_subscribed({"id": "test-id"}, r"foo"))

    def test_is_valid_clinic_code_true(self):
        """
        If there are results for the clinic code search, then True should be
        returned
        """
        ClinicCode.objects.create(
            code="123456", value="123456", uid="yGVQRg2PXNh", name="wc Test Clinic"
        )
        self.assertTrue(task.is_valid_clinic_code("123456"))

    def test_is_valid_clinic_code_false(self):
        """
        If there are no results for the clinic code search, then False should
        be returned
        """
        self.assertFalse(task.is_valid_clinic_code("123456"))

    @responses.activate
    def test_send_welcome_message_whatsapp(self):
        """
        Should escape formatting for the USSD codes, and send using the correct
        channel
        """
        responses.add(responses.POST, "http://ms/api/v1/outbound/")
        send_welcome_message("eng_ZA", "WHATSAPP", "+27820001000", "identity-uuid")
        request = responses.calls[-1].request
        self.assertEqual(
            json.loads(request.body),
            {
                "to_addr": "+27820001000",
                "to_identity": "identity-uuid",
                "channel": "JUNE_TEXT",
                "content": (
                    "Welcome! MomConnect will send helpful WhatsApp msgs. To stop dial "
                    '*134*550*1# (Free). To get msgs via SMS instead, reply "SMS" '
                    "(std rates apply)."
                ),
                "metadata": {},
            },
        )

    @responses.activate
    def test_send_welcome_message_sms(self):
        """
        Should send the SMS text using the correct channel and language
        """
        responses.add(responses.POST, "http://ms/api/v1/outbound/")
        send_welcome_message("nso_ZA", "JUNE_TEXT", "+27820001000", "identity-uuid")
        request = responses.calls[-1].request
        self.assertEqual(
            json.loads(request.body),
            {
                "to_addr": "+27820001000",
                "to_identity": "identity-uuid",
                "channel": "JUNE_TEXT",
                "content": "Congratulations on your pregnancy! MomConnect will send you "
                "helpful SMS msgs. To stop dial *134*550*1#, for more dial "
                "*134*550*7# (Free).",
                "metadata": {},
            },
        )

    @responses.activate
    def test_on_failure(self):
        """
        If there is a failure in processing the registration, then a webhook
        should be sent detailing the error
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
            },
        )

        responses.add(responses.POST, "http://testcallback/")

        self.assertRaises(KeyError, task.apply(args=(reg.pk,)).get)

        request = responses.calls[-1].request
        self.assertEqual(request.headers["Authorization"], "Bearer test-auth-token")
        callback = json.loads(request.body)
        reg.refresh_from_db()
        self.assertEqual(callback, reg.status)

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    @responses.activate
    def test_already_subscribed(self, get_identity, is_subscribed):
        """
        If the registrant is already subscribed to a prebirth message set,
        then the registration should not go through, and there should be a
        failure callback.
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
            },
        )

        responses.add(responses.POST, "http://testcallback")

        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = True
        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "registration_id": str(reg.pk),
                "registration_data": RegistrationSerializer(reg).data,
                "status": "validation_failed",
                "error": {
                    "mom_msisdn": "Number is already subscribed to MomConnect messaging"
                },
            },
        )

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    @responses.activate
    def test_opted_out_no_opt_in(self, get_identity, is_subscribed, opted_out):
        """
        If the registrant has previously opted out, and they haven't selected
        to opt in again, then the registration should not go through, and
        there should be a failure callback.
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_opt_in": False,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
            },
        )

        responses.add(responses.POST, "http://testcallback")
        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "registration_id": str(reg.pk),
                "registration_data": RegistrationSerializer(reg).data,
                "status": "validation_failed",
                "error": {
                    "mom_opt_in": (
                        "Mother has previously opted out and has not chosen to opt "
                        "back in again"
                    )
                },
            },
        )

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "opt_in"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    def test_opted_out_with_opt_in(
        self, get_identity, is_subscribed, opted_out, optin, whatsapp
    ):
        """
        If the registrant has previously opted out, and they have selected
        to opt in again, then it should opt them in again and continue
        the registration
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_opt_in": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
            },
        )

        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = True
        whatsapp.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        optin.assert_called_once_with({"id": "mother-id"}, "+27820000000", source)

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_subscriptionrequests"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_valid_clinic_code"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    def test_whatsapp_registration(
        self, get_identity, is_subscribed, opted_out, whatsapp, clinic, fail
    ):
        """
        If the registrant opted to receive messages on whatsapp, and they're
        registered on WhatsApp, then the resulting registration should be
        for whatsapp
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_whatsapp": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
                "faccode": "123456",
            },
        )

        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = True
        clinic.return_value = True
        fail.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        reg.refresh_from_db()
        self.assertEqual(reg.reg_type, "whatsapp_prebirth")
        self.assertEqual(reg.data["registered_on_whatsapp"], True)

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_subscriptionrequests"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_valid_clinic_code"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    def test_sms_registration(
        self, get_identity, is_subscribed, opted_out, whatsapp, clinic, fail
    ):
        """
        If the registrant opted to receive messages on whatsapp, but they're
        not registered on WhatsApp, then the resulting registration should be
        for sms
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_whatsapp": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
                "faccode": "123456",
            },
        )

        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True
        fail.side_effect = Exception()

        self.assertRaises(Exception, task, str(reg.pk))
        reg.refresh_from_db()
        self.assertEqual(reg.reg_type, "momconnect_prebirth")
        self.assertEqual(reg.data["registered_on_whatsapp"], False)

    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_valid_clinic_code"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    @responses.activate
    def test_invalid_clinic_code(
        self, get_identity, is_subscribed, opted_out, whatsapp, clinic
    ):
        """
        If the clinic code is invalid, then the registration should not
        validate, and an error webhook should be returned
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_whatsapp": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
                "faccode": "123456",
            },
        )

        responses.add(responses.POST, "http://testcallback/")
        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = False

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "registration_id": str(reg.pk),
                "registration_data": RegistrationSerializer(reg).data,
                "status": "validation_failed",
                "error": {"clinic_code": "Not a recognised clinic code"},
            },
        )

    @mock.patch("registrations.tasks.send_welcome_message")
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_subscriptionrequests"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_popi_subscriptionrequest"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_valid_clinic_code"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    @responses.activate
    def test_registration_complete_no_pmtct(
        self,
        get_identity,
        is_subscribed,
        opted_out,
        whatsapp,
        clinic,
        subreq,
        popi_subreq,
        welcome_msg,
    ):
        """
        Valid parameters should result in a successful registration and a
        success webhook being sent
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_whatsapp": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
                "faccode": "123456",
                "mom_pmtct": False,
                "language": "eng_ZA",
            },
        )

        responses.add(responses.POST, "http://testcallback/")
        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "registration_id": str(reg.pk),
                "registration_data": RegistrationSerializer(reg).data,
                "status": "succeeded",
            },
        )
        self.assertEqual(Registration.objects.count(), 1)

    @mock.patch("registrations.tasks.send_welcome_message")
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_pmtct_registration"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_subscriptionrequests"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "create_popi_subscriptionrequest"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_valid_clinic_code"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_registered_on_whatsapp"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration." "is_opted_out"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "is_identity_subscribed"
    )
    @mock.patch(
        "registrations.tasks.validate_subscribe_jembi_app_registration."
        "get_or_update_identity_by_address"
    )
    @responses.activate
    def test_registration_complete_with_pmtct(
        self,
        get_identity,
        is_subscribed,
        opted_out,
        whatsapp,
        clinic,
        subreq,
        popi_subreq,
        pmtct,
        welcome_msg,
    ):
        """
        Valid parameters should result in a successful registration and a
        success webhook being sent.
        """
        user = User.objects.create_user("test", "test@example.org", "test")
        source = Source.objects.create(
            name="testsource", user=user, authority="hw_full"
        )
        reg = Registration.objects.create(
            reg_type="jembi_momconnect",
            source=source,
            data={
                "msisdn_registrant": "+27820000000",
                "msisdn_device": "+27821111111",
                "mom_whatsapp": True,
                "callback_url": "http://testcallback",
                "callback_auth_token": "test-auth-token",
                "faccode": "123456",
                "mom_pmtct": True,
                "language": "eng_ZA",
            },
        )

        responses.add(responses.POST, "http://testcallback/")
        get_identity.return_value = {"id": "mother-id"}
        is_subscribed.return_value = False
        opted_out.return_value = False
        whatsapp.return_value = False
        clinic.return_value = True

        task(str(reg.pk))

        reg.refresh_from_db()
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "registration_id": str(reg.pk),
                "registration_data": RegistrationSerializer(reg).data,
                "status": "succeeded",
            },
        )
        pmtct.assert_called_with(reg, {"id": "mother-id"})


class ServiceInfoSubscriptionRequestTestCase(AuthenticatedAPITestCase):
    def test_skips_other_registration_types(self):
        """
        Should skip creating subscription requests if not a whatsapp
        registration
        """
        registration = Registration(reg_type="momconnect_prebirth")
        validate_subscribe.create_service_info_subscriptionrequest(registration)
        self.assertEqual(SubscriptionRequest.objects.count(), 0)

    def test_skips_other_authorities(self):
        """
        Should skip creating subscription requests if the source authority is
        partial or public
        """
        registration = Registration(
            source=self.make_source_partialuser(), reg_type="whatsapp_prebirth"
        )
        validate_subscribe.create_service_info_subscriptionrequest(registration)
        self.assertEqual(SubscriptionRequest.objects.count(), 0)


class GetWhatsAppContactTests(TestCase):
    @responses.activate
    def test_contact_returned(self):
        """
        If the API returns a contact, the ID should be saved in the database
        """
        self.assertEqual(WhatsAppContact.objects.count(), 0)
        responses.add(
            responses.POST,
            "http://engage/v1/contacts",
            json={
                "contacts": [
                    {"input": "+27820001001", "status": "valid", "wa_id": "27820001001"}
                ]
            },
        )
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "27820001001")

    @responses.activate
    def test_contact_not_returned(self):
        """
        If the API doesn't return a contact, the ID should be blank in the database
        """
        self.assertEqual(WhatsAppContact.objects.count(), 0)
        responses.add(
            responses.POST,
            "http://engage/v1/contacts",
            json={"contacts": [{"input": "+27820001001", "status": "invalid"}]},
        )
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "")

    @responses.activate
    def test_contact_exists_in_database(self):
        """
        If the contact already exists in the database, it should be returned
        """
        WhatsAppContact.objects.create(msisdn="+27820001001", whatsapp_id="27820001001")
        get_whatsapp_contact("+27820001001")

        [contact] = WhatsAppContact.objects.all()
        self.assertEqual(contact.msisdn, "+27820001001")
        self.assertEqual(contact.whatsapp_id, "27820001001")


class GetOrCreateIdentityFromMsisdnTaskTests(TestCase):
    @responses.activate
    def test_identity_exists(self):
        """
        If the identity exists, then we should add it to the context
        """
        identity = {
            "id": "test-identity-id",
            "details": {"addresses": {"msisdn": {"+27820001001": {}}}},
        }
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": [identity]},
        )
        result = get_or_create_identity_from_msisdn(
            {"identity-msisdn": "0820001001"}, "identity-msisdn"
        )
        self.assertEqual(
            result,
            {"identity-msisdn": "0820001001", "identity-msisdn_identity": identity},
        )

    @responses.activate
    def test_identity_does_not_exist(self):
        """
        If the identity does not exist, then we should create a new identity, and add
        it to the context
        """
        identity = {
            "id": "test-identity-id",
            "details": {
                "default_addr_type": "msisdn",
                "addresses": {"msisdn": {"+27820001001": {"default": True}}},
            },
        }
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": []},
        )
        responses.add(responses.POST, "http://is/api/v1/identities/", json=identity)

        result = get_or_create_identity_from_msisdn(
            {"identity-msisdn": "0820001001"}, "identity-msisdn"
        )
        self.assertEqual(
            result,
            {"identity-msisdn": "0820001001", "identity-msisdn_identity": identity},
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {"details": identity["details"]},
        )


class UpdateIdentityFromRapidProClinicRegistrationTaskTests(TestCase):
    @responses.activate
    def test_sa_id(self):
        """
        SA ID registrations should update the SA ID and DoB fields
        """
        responses.add(responses.PATCH, "http://is/api/v1/identities/test-id/", json={})
        update_identity_from_rapidpro_clinic_registration(
            {
                "mom_msisdn_identity": {"id": "test-id", "details": {}},
                "mom_lang": "eng_ZA",
                "mom_id_type": "sa_id",
                "mom_sa_id_no": "8606045069081",
                "registration_type": "prebirth",
                "mom_edd": "2019-12-12",
            }
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "details": {
                    "consent": True,
                    "lang_code": "eng_ZA",
                    "last_edd": "2019-12-12",
                    "last_mc_reg_on": "clinic",
                    "mom_dob": "1986-06-04",
                    "sa_id_no": "8606045069081",
                }
            },
        )

    @responses.activate
    def test_passport(self):
        """
        Passport registrations should update the passport number and origin fields
        """
        responses.add(responses.PATCH, "http://is/api/v1/identities/test-id/", json={})
        update_identity_from_rapidpro_clinic_registration(
            {
                "mom_msisdn_identity": {"id": "test-id", "details": {}},
                "mom_lang": "eng_ZA",
                "mom_id_type": "passport",
                "mom_passport_no": "123456789",
                "mom_passport_origin": "na",
                "registration_type": "postbirth",
                "baby_dob": "2019-01-01",
            }
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "details": {
                    "consent": True,
                    "lang_code": "eng_ZA",
                    "last_baby_dob": "2019-01-01",
                    "last_mc_reg_on": "clinic",
                    "passport_no": "123456789",
                    "passport_origin": "na",
                }
            },
        )

    @responses.activate
    def test_dob(self):
        """
        Date of birth registrations should update the date of birth
        """
        responses.add(responses.PATCH, "http://is/api/v1/identities/test-id/", json={})
        update_identity_from_rapidpro_clinic_registration(
            {
                "mom_msisdn_identity": {"id": "test-id", "details": {}},
                "mom_lang": "eng_ZA",
                "mom_id_type": "none",
                "mom_dob": "1986-06-04",
                "registration_type": "postbirth",
                "baby_dob": "2019-01-01",
            }
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "details": {
                    "consent": True,
                    "lang_code": "eng_ZA",
                    "last_baby_dob": "2019-01-01",
                    "last_mc_reg_on": "clinic",
                    "mom_dob": "1986-06-04",
                }
            },
        )


class UpdateIdentityFromRapidProPublicRegistrationTaskTests(TestCase):
    @responses.activate
    def test_update_fields(self):
        """
        Should update the identity detail fields
        """
        responses.add(responses.PATCH, "http://is/api/v1/identities/test-id/", json={})
        update_identity_from_rapidpro_public_registration(
            {
                "mom_msisdn_identity": {"id": "test-id", "details": {}},
                "mom_lang": "eng_ZA",
            }
        )
        self.assertEqual(
            json.loads(responses.calls[-1].request.body),
            {
                "details": {
                    "consent": True,
                    "lang_code": "eng_ZA",
                    "last_mc_reg_on": "public",
                }
            },
        )


class CreateRapidProClinicRegistrationTaskTests(AuthenticatedAPITestCase):
    def test_sa_id(self):
        """
        SA ID registrations should store the ID number and date of birth on the
        registration
        """
        source = self.make_source_normaluser()
        _create_rapidpro_clinic_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_msisdn_identity": {"id": "test-id"},
                "device_msisdn": "+27820001002",
                "device_msisdn_identity": {"id": "device-test-id"},
                "mom_lang": "eng_ZA",
                "mom_id_type": "sa_id",
                "mom_sa_id_no": "8606045069081",
                "registration_type": "prebirth",
                "channel": "SMS",
                "mom_edd": "2019-12-12",
                "clinic_code": "123456",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "momconnect_prebirth")
        self.assertEqual(reg.registrant_id, "test-id")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "edd": "2019-12-12",
                "faccode": "123456",
                "id_type": "sa_id",
                "language": "eng_ZA",
                "sa_id_no": "8606045069081",
                "mom_dob": "1986-06-04",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "operator_id": "device-test-id",
                "mha": 6,
            },
        )

    def test_passport(self):
        """
        Passport registrations should store the passport number and source on the
        registration
        """
        source = self.make_source_normaluser()
        _create_rapidpro_clinic_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_msisdn_identity": {"id": "test-id"},
                "device_msisdn": "+27820001002",
                "device_msisdn_identity": {"id": "device-test-id"},
                "mom_lang": "eng_ZA",
                "mom_id_type": "passport",
                "mom_passport_no": "123456789",
                "mom_passport_origin": "na",
                "registration_type": "prebirth",
                "channel": "WhatsApp",
                "mom_edd": "2019-12-12",
                "clinic_code": "123456",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "whatsapp_prebirth")
        self.assertEqual(reg.registrant_id, "test-id")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "edd": "2019-12-12",
                "faccode": "123456",
                "id_type": "passport",
                "passport_no": "123456789",
                "passport_origin": "na",
                "language": "eng_ZA",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "operator_id": "device-test-id",
                "mha": 6,
            },
        )

    def test_dob(self):
        """
        Date of birth registrations should store the date of birth on the registration
        """
        source = self.make_source_normaluser()
        _create_rapidpro_clinic_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_msisdn_identity": {"id": "test-id"},
                "device_msisdn": "+27820001002",
                "device_msisdn_identity": {"id": "device-test-id"},
                "mom_lang": "eng_ZA",
                "mom_id_type": "none",
                "mom_dob": "1986-06-04",
                "registration_type": "postbirth",
                "channel": "SMS",
                "baby_dob": "2019-01-01",
                "clinic_code": "123456",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "momconnect_postbirth")
        self.assertEqual(reg.registrant_id, "test-id")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "baby_dob": "2019-01-01",
                "faccode": "123456",
                "id_type": "none",
                "mom_dob": "1986-06-04",
                "language": "eng_ZA",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "operator_id": "device-test-id",
                "mha": 6,
            },
        )

    def test_whatsapp_postbirth(self):
        """
        A channel of WhatsApp and registration type of postbirth should create a
        whatsapp_postbirth type registration
        """
        source = self.make_source_normaluser()
        _create_rapidpro_clinic_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_msisdn_identity": {"id": "test-id"},
                "device_msisdn": "+27820001002",
                "device_msisdn_identity": {"id": "device-test-id"},
                "mom_lang": "eng_ZA",
                "mom_id_type": "none",
                "mom_dob": "1986-06-04",
                "registration_type": "postbirth",
                "channel": "WhatsApp",
                "baby_dob": "2019-01-01",
                "clinic_code": "123456",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "whatsapp_postbirth")
        self.assertEqual(reg.registrant_id, "test-id")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "baby_dob": "2019-01-01",
                "faccode": "123456",
                "id_type": "none",
                "mom_dob": "1986-06-04",
                "language": "eng_ZA",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "operator_id": "device-test-id",
                "mha": 6,
            },
        )

    @responses.activate
    def test_end_to_end(self):
        """
        Ensure that the chaining of tasks works
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": [{"id": "test-id-1", "details": {}}]},
        )
        responses.add(
            responses.PATCH,
            "http://is/api/v1/identities/test-id-1/",
            json={"id": "test-id-1", "details": {}},
        )
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001002"})
            ),
            json={"results": [{"id": "test-id-2", "details": {}}]},
        )
        source = self.make_source_normaluser()
        create_rapidpro_clinic_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "device_msisdn": "+27820001002",
                "mom_lang": "eng_ZA",
                "mom_id_type": "sa_id",
                "mom_sa_id_no": "8606045069081",
                "registration_type": "prebirth",
                "channel": "SMS",
                "mom_edd": "2019-12-12",
                "clinic_code": "123456",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "momconnect_prebirth")
        self.assertEqual(reg.registrant_id, "test-id-1")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "edd": "2019-12-12",
                "faccode": "123456",
                "id_type": "sa_id",
                "language": "eng_ZA",
                "sa_id_no": "8606045069081",
                "mom_dob": "1986-06-04",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "operator_id": "test-id-2",
                "mha": 6,
            },
        )


class CreateRapidProPublicRegistrationTaskTests(AuthenticatedAPITestCase):
    def test_create_registration(self):
        """
        Should create a registration with the appropriate details
        """
        source = self.make_source_normaluser()
        _create_rapidpro_public_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_msisdn_identity": {"id": "test-id"},
                "mom_lang": "eng_ZA",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "whatsapp_prebirth")
        self.assertEqual(reg.registrant_id, "test-id")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "language": "eng_ZA",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001001",
                "operator_id": "test-id",
                "registered_on_whatsapp": True,
                "mha": 6,
            },
        )

    @responses.activate
    def test_end_to_end(self):
        """
        Ensure that the chaining of tasks works
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": [{"id": "test-id-1", "details": {}}]},
        )
        responses.add(
            responses.PATCH,
            "http://is/api/v1/identities/test-id-1/",
            json={"id": "test-id-1", "details": {}},
        )
        source = self.make_source_normaluser()
        create_rapidpro_public_registration(
            {
                "user_id": self.normaluser.id,
                "mom_msisdn": "+27820001001",
                "mom_lang": "eng_ZA",
            }
        )
        [reg] = Registration.objects.all()
        self.assertEqual(reg.reg_type, "whatsapp_prebirth")
        self.assertEqual(reg.registrant_id, "test-id-1")
        self.assertEqual(reg.source, source)
        self.assertEqual(
            reg.data,
            {
                "consent": True,
                "language": "eng_ZA",
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001001",
                "operator_id": "test-id-1",
                "registered_on_whatsapp": True,
                "mha": 6,
            },
        )


class ValidateSubscribePostbirthTests(AuthenticatedAPITestCase):
    def test_validation_missing_fields_failure(self):
        """
        Should give details on the fields that are missing
        """
        registration = Registration.objects.create(
            reg_type="momconnect_postbirth",
            source=self.make_source_adminuser(),
            registrant_id=str(uuid4()),
            data={},
        )
        result = validate_subscribe.validate(registration)
        self.assertFalse(result)
        errors = registration.data["invalid_fields"]
        self.assertIn("Operator ID missing", errors)
        self.assertIn("MSISDN of Registrant missing", errors)
        self.assertIn("MSISDN of device missing", errors)
        self.assertIn("Language is missing from data", errors)
        self.assertIn("Consent is missing", errors)
        self.assertIn("ID type missing", errors)
        self.assertIn("Baby Date of Birth missing", errors)
        self.assertIn("Facility (clinic) code missing", errors)

    def test_validation_incorrect_fields(self):
        """
        Should give details on fields that are incorrect
        """
        registration = Registration.objects.create(
            reg_type="whatsapp_postbirth",
            source=self.make_source_adminuser(),
            registrant_id=str(uuid4()),
            data={
                "operator_id": "1",
                "msisdn_registrant": "2",
                "msisdn_device": "3",
                "language": "4",
                "consent": False,
                "id_type": "5",
                "baby_dob": "6",
                "faccode": "",
            },
        )
        result = validate_subscribe.validate(registration)
        self.assertFalse(result)
        errors = registration.data["invalid_fields"]
        self.assertIn("Operator ID invalid", errors)
        self.assertIn("MSISDN of Registrant invalid", errors)
        self.assertIn("MSISDN of device invalid", errors)
        self.assertIn("Language not a valid option", errors)
        self.assertIn("Cannot continue without consent", errors)
        self.assertIn("ID type should be one of ['sa_id', 'passport', 'none']", errors)
        self.assertIn("Baby Date of Birth invalid", errors)
        self.assertIn("Facility code invalid", errors)

    def test_public_registration_validation_failure(self):
        """
        Public registration is not yet supported for postbirth
        """
        registration = Registration.objects.create(
            reg_type="momconnect_postbirth",
            source=self.make_source_normaluser(),
            registrant_id=str(uuid4()),
            data={},
        )
        result = validate_subscribe.validate(registration)
        self.assertFalse(result)
        errors = registration.data["invalid_fields"]
        self.assertIn(
            "Momconnect postbirth not yet supported for public or CHW", errors
        )

    def test_validation_success(self):
        """
        If the data is correct, then the validation should succeed
        """
        registration = Registration.objects.create(
            reg_type="momconnect_postbirth",
            source=self.make_source_adminuser(),
            registrant_id=str(uuid4()),
            data={
                "operator_id": str(uuid4()),
                "msisdn_registrant": "+27820001001",
                "msisdn_device": "+27820001002",
                "language": "eng_ZA",
                "consent": True,
                "id_type": "sa_id",
                "sa_id_no": "8108015001051",
                "mom_dob": "1981-08-01",
                "baby_dob": "2015-01-01",
                "faccode": "123456",
            },
        )
        result = validate_subscribe.validate(registration)
        self.assertTrue(result)


class OptInIdentityTestCase(TestCase):
    @responses.activate
    def test_not_opted_out(self):
        """
        If the address on the identity isn't opted out, then we should do nothing
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/identity-uuid/",
            json={
                "details": {
                    "addresses": {"msisdn": {"+27820001001": {"optedout": False}}}
                }
            },
        )
        opt_in_identity("identity-uuid", "+27820001001", 1)

    @responses.activate
    def test_opted_out(self):
        """
        If the address on the identity is opted out, then we should create an opt in
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user, name="Test name")

        responses.add(
            responses.GET,
            "http://is/api/v1/identities/identity-uuid/",
            json={
                "details": {
                    "addresses": {"msisdn": {"+27820001001": {"optedout": True}}}
                }
            },
        )

        responses.add(responses.POST, "http://is/api/v1/optin/")

        opt_in_identity("identity-uuid", "+27820001001", source.id)

        request = responses.calls[-1].request
        self.assertEqual(
            json.loads(request.body),
            {
                "address": "+27820001001",
                "address_type": "msisdn",
                "identity": "identity-uuid",
                "request_source": "Test name",
                "requestor_source_id": source.id,
            },
        )
