import json
from datetime import datetime, timedelta
from unittest import mock
from urllib.parse import urlencode

import responses
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.test import TestCase
from rest_hooks.models import model_saved

from changes.models import Change
from changes.signals import psh_validate_implement
from changes.tasks import (
    get_engage_inbound_and_reply,
    get_identity_from_msisdn,
    get_text_or_caption_from_turn_message,
    process_engage_helpdesk_outbound,
    process_whatsapp_contact_check_fail,
    process_whatsapp_system_event,
    process_whatsapp_timeout_system_event,
    process_whatsapp_unsent_event,
    refresh_engage_context,
    send_helpdesk_response_to_dhis2,
)
from ndoh_hub import utils
from registrations.models import Registration, Source
from registrations.signals import psh_validate_subscribe


class DisconnectRegistrationSignalsMixin(object):
    def setUp(self):
        assert post_save.has_listeners(Registration), (
            "Registration model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )
        post_save.disconnect(
            receiver=psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )
        post_save.disconnect(receiver=model_saved, dispatch_uid="instance-saved-hook")
        assert not post_save.has_listeners(Registration), (
            "Registration model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests."
        )
        return super().setUp()

    def tearDown(self):
        assert not post_save.has_listeners(Registration), (
            "Registration model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests."
        )
        post_save.connect(
            psh_validate_subscribe,
            sender=Registration,
            dispatch_uid="psh_validate_subscribe",
        )
        post_save.connect(receiver=model_saved, dispatch_uid="instance-saved-hook")
        return super().tearDown()


class WhatsAppBaseTestCase(TestCase):
    def create_outbound_lookup(self, result_count=1):

        results = []
        for i in range(0, result_count):
            results.append({"to_identity": "test-identity-uuid"})

        responses.add(
            responses.GET,
            "http://ms/api/v1/outbound/?vumi_message_id=messageid",
            json={"results": results},
            status=200,
            match_querystring=True,
        )

    def update_identity_lookup(self, lang="eng_ZA"):
        responses.add(
            responses.PATCH,
            "http://is/api/v1/identities/test-identity-uuid/",
            json={
                "id": "test_identity-uuid",
                "details": {"lang_code": lang, "timeout_timestamp": "time"},
            },
            status=200,
            match_querystring=True,
        )

    def create_identity_lookup(self, lang="eng_ZA"):
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/test-identity-uuid/",
            json={"id": "test_identity-uuid", "details": {"lang_code": lang}},
            status=200,
            match_querystring=True,
        )

    def create_identity_lookup_with_timestamp(self, timestamp):
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/test-identity-uuid/",
            json={
                "id": "test_identity-uuid",
                "details": {"lang_code": "eng_ZA", "timeout_timestamp": timestamp},
            },
            status=200,
            match_querystring=True,
        )

    def create_identity_lookup_by_msisdn(
        self, address="+27820001001", lang="eng_ZA", num_results=1
    ):
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": address})
            ),
            json={
                "results": [
                    {"id": "test-identity-uuid", "details": {"lang_code": lang}}
                ]
                * num_results
            },
            status=200,
            match_querystring=True,
        )


class ProcessWhatsAppUnsentEventTaskTests(WhatsAppBaseTestCase):
    def setUp(self):
        post_save.disconnect(receiver=psh_validate_implement, sender=Change)

    def tearDown(self):
        post_save.connect(receiver=psh_validate_implement, sender=Change)

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_change_created(self, mock_create_outbound):
        """
        The task should create a Change according to the details received from the
        message sender
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)

        self.create_outbound_lookup()
        self.create_identity_lookup()

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event(
            "messageid",
            source.pk,
            [
                {
                    "code": 500,
                    "title": (
                        "structure unavailable: Client could not display highly "
                        "structured message"
                    ),
                }
            ],
        )

        [change] = Change.objects.all()
        self.assertEqual(change.registrant_id, "test-identity-uuid")
        self.assertEqual(change.action, "switch_channel")
        self.assertEqual(
            change.data, {"channel": "sms", "reason": "whatsapp_unsent_event"}
        )
        self.assertEqual(change.created_by, user)

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test-identity-uuid",
                "content": (
                    "Sorry we can't send WhatsApp msgs to this phone. We'll send your MomConnect "
                    "msgs on SMS. To stop dial *134*550*1#, for more dial *134*550*7#"
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_change_created_diff_language(self, mock_create_outbound):
        """
        The task should create a Change according to the details received from
        the message sender
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)

        self.create_outbound_lookup()
        self.create_identity_lookup("zul_ZA")

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event(
            "messageid",
            source.pk,
            [
                {
                    "code": 500,
                    "title": (
                        "structure unavailable: Client could not display highly "
                        "structured message"
                    ),
                }
            ],
        )

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test-identity-uuid",
                "content": (
                    "Sorry we can't send WhatsApp msgs to this phone. "
                    "We'll send your MomConnect msgs on SMS. To stop dial *134*550*1#, "
                    "for more dial *134*550*7#"
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @responses.activate
    def test_no_outbound_message(self):
        """
        If no outbound message can be found, then the change shouldn't be
        created
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)

        self.create_outbound_lookup(0)

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event(
            "messageid",
            source.pk,
            [
                {
                    "code": 500,
                    "title": (
                        "structure unavailable: Client could not display highly "
                        "structured message"
                    ),
                }
            ],
        )

        self.assertEqual(Change.objects.count(), 0)

    @responses.activate
    def test_non_hsm_failure(self):
        """
        The task should not create a switch if it is not a hsm failure
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)

        self.create_outbound_lookup(1)

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event(
            "messageid",
            source.pk,
            [{"code": 200, "title": "random error: temporary random error"}],
        )

        self.assertEqual(Change.objects.count(), 0)


class ProcessWhatsAppSystemEventTaskTests(WhatsAppBaseTestCase):
    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_message_sent_delivered(self, mock_create_outbound):
        """
        The task should send the correct outbound based on the delivered event.
        """
        self.create_outbound_lookup()
        self.create_identity_lookup()

        process_whatsapp_system_event("messageid", "undelivered")

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test-identity-uuid",
                "content": (
                    "We see that your MomConnect WhatsApp messages are not being "
                    "delivered. If you would like to receive your messages over SMS, "
                    "reply ‘SMS’."
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_no_message_sent(self, mock_create_outbound):
        """
        The task should not create a Outbound when the event is the wrong type.
        """
        self.create_outbound_lookup()

        process_whatsapp_system_event("messageid", "something_else")

        self.assertFalse(mock_create_outbound.called)

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_no_message_found(self, mock_create_outbound):
        """
        The task should not create a outbound if the original message was not
        found
        """
        self.create_outbound_lookup(0)

        process_whatsapp_system_event("messageid", "undelivered")

        self.assertEqual(
            responses.calls[0].request.url,
            "http://ms/api/v1/outbound/?vumi_message_id=messageid",
        )
        self.assertFalse(mock_create_outbound.called)

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @mock.patch("changes.tasks.is_client.update_identity")
    @mock.patch("changes.tasks.get_utc_now")
    @responses.activate
    def test_timeout_error(
        self, mock_get_utc_now, mock_update_identity, mock_create_outbound
    ):
        """
        The task should send the correct outbound based on the delivered event,
        for a timeout error
        """
        self.create_outbound_lookup()
        self.create_identity_lookup()
        self.update_identity_lookup()

        timestamp = 1543999390.069308
        mock_get_utc_now.return_value = datetime.fromtimestamp(timestamp)

        process_whatsapp_timeout_system_event.delay({"message_id": "messageid"}).get()

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test_identity-uuid",
                "content": (
                    "We see that your MomConnect WhatsApp messages are not being "
                    "delivered. If you would like to receive your messages over "
                    "SMS, reply ‘SMS’."
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

        mock_update_identity.assert_called_once_with(
            "test_identity-uuid",
            {"details": {"lang_code": "eng_ZA", "timeout_timestamp": timestamp}},
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @mock.patch("changes.tasks.is_client.update_identity")
    @mock.patch("changes.tasks.get_utc_now")
    @responses.activate
    def test_timeout_error_with_timestamp(
        self, mock_get_utc_now, mock_update_identiity, mock_create_outbound
    ):
        """
        The task should send the correct outbound based on the delivered event,
        for a timeout error
        """
        timestamp = 1543999390.069308
        date = mock_get_utc_now.return_value = datetime.fromtimestamp(timestamp)

        date_N_days_ago = date - timedelta(days=31)
        timeout_timestamp = date_N_days_ago.timestamp()

        self.create_outbound_lookup()
        self.create_identity_lookup_with_timestamp(timeout_timestamp)
        self.update_identity_lookup()

        process_whatsapp_timeout_system_event.delay({"message_id": "messageid"}).get()

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test_identity-uuid",
                "content": (
                    "We see that your MomConnect WhatsApp messages are not being "
                    "delivered. If you would like to receive your messages over "
                    "SMS, reply ‘SMS’."
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

        mock_update_identiity.assert_called_once_with(
            "test_identity-uuid",
            {"details": {"lang_code": "eng_ZA", "timeout_timestamp": timestamp}},
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @mock.patch("changes.tasks.is_client.update_identity")
    @mock.patch("changes.tasks.get_utc_now")
    @responses.activate
    def test_timeout_error_no_outbound_send(
        self, mock_get_utc_now, mock_update_identiity, mock_create_outbound
    ):
        """
        The task should not create a outbound if number of days since
        last send has not exceeded WHATSAPP_EXPIRY_SMS_BOUNCE_DAYS
        found
        """
        timestamp = 1543999390.069309
        date = mock_get_utc_now.return_value = datetime.fromtimestamp(timestamp)

        date_N_days_ago = date - timedelta(days=21)
        timeout_timestamp = date_N_days_ago.timestamp()

        self.create_outbound_lookup()
        self.create_identity_lookup_with_timestamp(timeout_timestamp)
        self.update_identity_lookup()

        process_whatsapp_timeout_system_event.delay({"message_id": "messageid"}).get()

        self.assertFalse(mock_create_outbound.called)
        self.assertFalse(mock_update_identiity.called)


class ProcessWhatsAppContactLookupFailTaskTests(WhatsAppBaseTestCase):
    def setUp(self):
        post_save.disconnect(receiver=psh_validate_implement, sender=Change)

    def tearDown(self):
        post_save.connect(receiver=psh_validate_implement, sender=Change)

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_successful_processing(self, mock_create_outbound):
        """
        The task should send the correct outbound based on the contact lookup
        failure hook.
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        self.create_identity_lookup_by_msisdn(address="+27820001001")

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_contact_check_fail(user.pk, "+27820001001")

        [change] = Change.objects.all()
        self.assertEqual(change.registrant_id, "test-identity-uuid")
        self.assertEqual(change.action, "switch_channel")
        self.assertEqual(
            change.data, {"channel": "sms", "reason": "whatsapp_contact_check_fail"}
        )
        self.assertEqual(change.created_by, user)
        self.assertEqual(change.source, source)

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test-identity-uuid",
                "content": (
                    "Oh no! You can't get MomConnect messages on WhatsApp. "
                    "We'll keep sending your MomConnect messages on SMS."
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @mock.patch("changes.tasks.utils.ms_client.create_outbound")
    @responses.activate
    def test_sms_language(self, mock_create_outbound):
        """
        The outbound SMS should be translated into the user's language
        """
        user = User.objects.create_user("test")
        Source.objects.create(user=user)
        self.create_identity_lookup_by_msisdn(address="+27820001001", lang="xho_ZA")

        process_whatsapp_contact_check_fail(user.pk, "+27820001001")

        mock_create_outbound.assert_called_once_with(
            {
                "to_identity": "test-identity-uuid",
                "content": (
                    "Oh no! You can't get MomConnect messages on WhatsApp. "
                    "We'll keep sending your MomConnect messages on SMS."
                ),
                "channel": "JUNE_TEXT",
                "metadata": {},
            }
        )

    @responses.activate
    def test_no_identity_found(self):
        """
        If there's no identity for the given msisdn, the task should exit
        without taking any actions
        """
        user = User.objects.create_user("test")
        self.create_identity_lookup_by_msisdn(num_results=0)

        process_whatsapp_contact_check_fail(user.pk, "+27820001001")

        self.assertEqual(Change.objects.count(), 0)


class GetEngageInboundAndReplyTests(TestCase):
    @responses.activate
    def test_get_engage_inbound_and_reply(self):
        message_id = "BCGGJ3FVFUV"
        responses.add(
            responses.GET,
            "http://engage/v1/contacts/27820001001/messages",
            status=200,
            json={
                "messages": [
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "in_reply_to": "KCGGK3FVGUV_CiD9cD-KZ7S6UsB76FeJP3sc",
                                "author": {
                                    "id": "2ab15df1-082a-4420-8f1a-1fed53b13eba",
                                    "name": "Operator Name",
                                    "type": "OPERATOR",
                                },
                            }
                        },
                        "from": "27820001002",
                        "id": "gBGGJ3EVEUV_AgkC5c71UQ9ug08",
                        "text": {"body": "Response after the one we care about"},
                        "timestamp": "1540803400",
                        "type": "text",
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "in_reply_to": "gBGGJ3EVEUV_AgkC5c71UQ9ug08",
                                "author": {
                                    "id": "2ab15df1-082a-4420-8f1a-1fed53b13eba",
                                    "name": "Operator Name",
                                    "type": "OPERATOR",
                                },
                            }
                        },
                        "from": "27820001002",
                        "id": message_id,
                        "text": {"body": "Operator response"},
                        "timestamp": "1540803363",
                        "type": "text",
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "in_reply_to": "ABGGJ3EVEUV_AhC9cG-UA8S5UsB75FeJP1sb",
                                "author": {
                                    "id": "6a6d72e8-295d-4a57-bd8a-6fdca598f9a6",
                                    "name": "Autoresponse Name",
                                    "type": "SYSTEM",
                                },
                            }
                        },
                        "from": "27820001002",
                        "id": "gBGGJ3EVEUV_AgkC5c71UQ9ug08",
                        "text": {"body": "Autoresponse - should be ignored"},
                        "timestamp": "1540803295",
                        "type": "text",
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "inbound",
                                "in_reply_to": None,
                                "labels": [
                                    {
                                        "uuid": "cbaf27bc-2ba9-4e4a-84c1-098d5abd80bf",
                                        "value": "image",
                                    }
                                ],
                                "inserted_at": "2018-10-29T08:54:53.123456Z",
                            }
                        },
                        "from": "27820001001",
                        "id": "ABGGJ3EVEUV_AhC9cG-UA8S5UsA75FeJP1sb",
                        "image": {
                            "caption": "User question as caption",
                            "file": "/path/to/media/file",
                            "id": "1260423b-b39a-4283-ba85-623f81f9408d",
                            "mime_type": "image/jpeg",
                            "sha256": "f706688d5fc79cd0640cd39086dd3f3885708b7fe2e64fd",
                        },
                        "timestamp": None,
                        "type": None,
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "inbound",
                                "in_reply_to": None,
                                "labels": [
                                    {
                                        "uuid": "cbaf27bc-2ba9-4e4a-84c1-098d5abd80be",
                                        "value": "text",
                                    }
                                ],
                            }
                        },
                        "from": "27820001001",
                        "id": "ABGGJ3EVEUV_AhALwhRTSopsSmF7IxgeYIBz",
                        "text": {"body": "User question as text"},
                        "timestamp": "1540802983",
                        "type": "text",
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "in_reply_to": "BCGGJ3FVFUV_CiC9cG-KZ7S5UsB73FeJP2sc",
                                "author": {
                                    "id": "2ab15df1-082a-4420-8f1a-1fed53b13eba",
                                    "name": "Operator Name",
                                    "type": "OPERATOR",
                                },
                            }
                        },
                        "from": "27820001002",
                        "id": "gBGGJ3EVEUV_AgkC5c71UQ9ug08",
                        "text": {"body": "Previous operator response, should ignore"},
                        "timestamp": "1540802812",
                        "type": "text",
                    },
                    {
                        "_vnd": {"v1": {"direction": "inbound", "in_reply_to": None}},
                        "from": "27820001001",
                        "id": "GBFGJ8EVEUV_AhBLwhRTSpprSmF7IxhfYIBy",
                        "text": {"body": "Previous user question, should be ignored"},
                        "timestamp": "1540802744",
                        "type": "text",
                    },
                ]
            },
        )
        resp = get_engage_inbound_and_reply.delay("27820001001", message_id)
        self.assertEqual(
            resp.get(),
            {
                "inbound_address": "27820001001",
                "inbound_text": "User question as text | User question as caption",
                "inbound_timestamp": 1540803293.123456,
                "inbound_labels": ["image", "text"],
                "reply_text": "Operator response",
                "reply_timestamp": 1540803363,
                "reply_operator": 56748517727534413379787391391214157498,
            },
        )


class TestGetTextOrCaptionFromTurnMessage(TestCase):
    def test_text_type_body(self):
        """
        If the message is a text, the body should be returned.
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "from": "16315551234",
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "timestamp": "1518694235",
                    "text": {"body": "Hello this is an answer"},
                    "type": "text",
                }
            ),
            "Hello this is an answer",
        )

    def test_media_type_caption(self):
        """
        If the message is one of the known media types, the caption should be returned
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "from": "16315551234",
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "image": {
                        "file": (
                            "/usr/local/wamedia/shared/"
                            "b1cf38-8734-4ad3-b4a1-ef0c10d0d683"
                        ),
                        "id": "b1c68f38-8734-4ad3-b4a1-ef0c10d683",
                        "mime_type": "image/jpeg",
                        "sha256": (
                            "29ed500fa64eb55fc19dc4124acb300e5dcc54a0f822a301ae99944db"
                        ),
                        "caption": "Check out my new phone!",
                    },
                    "timestamp": "1521497954",
                    "type": "image",
                }
            ),
            "Check out my new phone!",
        )

    def test_media_type_no_caption(self):
        """
        If the message is one of the known media types, and there is no caption, the
        message type should be returned
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "from": "16315551234",
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "image": {
                        "file": (
                            "/usr/local/wamedia/shared/"
                            "b1cf38-8734-4ad3-b4a1-ef0c10d0d683"
                        ),
                        "id": "b1c68f38-8734-4ad3-b4a1-ef0c10d683",
                        "mime_type": "image/jpeg",
                        "sha256": (
                            "29ed500fa64eb55fc19dc4124acb300e5dcc54a0f822a301ae99944db"
                        ),
                    },
                    "timestamp": "1521497954",
                    "type": "image",
                }
            ),
            "<image>",
        )

    def test_contacts_type(self):
        """
        If it's a contacts message type, the string <contacts> should be returned
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "contacts": [
                        {
                            "addresses": [
                                {
                                    "city": "Menlo Park",
                                    "country": "United States",
                                    "country_code": "us",
                                    "state": "CA",
                                    "street": "1 Hacker Way",
                                    "type": "WORK",
                                    "zip": "94025",
                                }
                            ],
                            "birthday": "2012-08-18",
                            "emails": [{"email": "kfish@fb.com", "type": "WORK"}],
                            "name": {
                                "first_name": "Kerry",
                                "formatted_name": "Kerry Fisher",
                                "last_name": "Fisher",
                            },
                            "org": {"company": "Facebook"},
                            "phones": [
                                {"phone": "+1 (940) 555-1234", "type": "CELL"},
                                {
                                    "phone": "+1 (650) 555-1234",
                                    "type": "WORK",
                                    "wa_id": "16505551234",
                                },
                            ],
                            "urls": [
                                {"url": "https://www.facebook.com", "type": "WORK"}
                            ],
                        }
                    ],
                    "from": "16505551234",
                    "id": "ABGGFlA4dSRvAgo6C4Z53hMh1ugR",
                    "timestamp": "1537248012",
                    "type": "contacts",
                }
            ),
            "<contacts>",
        )

    def test_location_type(self):
        """
        If the message is a location type, the logitude and latitude should be returned
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "from": "16315551234",
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "location": {
                        "address": "Main Street Beach, Santa Cruz, CA",
                        "latitude": 38.9806263495,
                        "longitude": -131.9428612257,
                        "name": "Main Street Beach",
                        "url": "https://foursquare.com/v/4d7031d35b5df7744",
                    },
                    "timestamp": "1521497875",
                    "type": "location",
                }
            ),
            "<location 38.9806263495,-131.9428612257>",
        )

    def test_unknown_type(self):
        """
        The unknown message type should return <unknown>
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "errors": [
                        {
                            "code": 501,
                            "details": "Message type is not currently supported",
                            "title": "Unknown message type",
                        }
                    ],
                    "from": "16315551234",
                    "id": "ABGGFRBzFymPAgo6N9KKs7HsN6eB",
                    "timestamp": "1531933468",
                    "type": "unknown",
                }
            ),
            "<unknown>",
        )

    def test_null_type(self):
        """
        The null message type should return <unknown>
        """
        self.assertEqual(
            get_text_or_caption_from_turn_message(
                {
                    "from": "16315551234",
                    "id": "ABGGFRBzFymPAgo6N9KKs7HsN6eB",
                    "timestamp": None,
                    "type": None,
                }
            ),
            "<unknown>",
        )


class SendHelpdeskResponseToDHIS2Tests(DisconnectRegistrationSignalsMixin, TestCase):
    @responses.activate
    def test_send_helpdesk_response_to_dhis2(self):
        """
        Should send the data to OpenHIM in the correct format to be placed in DHIS2
        """
        message_id = "BCGGJ3FVFUV"

        def assert_openhim_request(request):
            payload = json.loads(request.body)
            self.assertEqual(
                payload,
                {
                    "encdate": "20181029085453",
                    "repdate": "20181029085603",
                    "mha": 1,
                    "swt": 4,
                    "cmsisdn": "+27820001001",
                    "dmsisdn": "+27820001001",
                    "faccode": "123456",
                    "data": {
                        "question": "Mother question",
                        "answer": "Operator answer",
                    },
                    "class": "label1,label2",
                    "type": 7,
                    "op": "104296490747485586223672247128147036730",
                    "eid": message_id,
                    "sid": "identity-uuid",
                },
            )
            return (200, {}, json.dumps({}))

        responses.add_callback(
            responses.POST,
            "http://jembi/ws/rest/v1/helpdesk",
            callback=assert_openhim_request,
            content_type="application/json",
        )

        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        Registration.objects.create(
            registrant_id="identity-uuid", data={"faccode": "123456"}, source=source
        )

        send_helpdesk_response_to_dhis2.apply_async(
            args=[
                {
                    "inbound_text": "Mother question",
                    "inbound_timestamp": "1540803293",
                    "inbound_address": "27820001001",
                    "reply_text": "Operator answer",
                    "reply_timestamp": "1540803363",
                    "reply_operator": 104296490747485586223672247128147036730,
                    "identity_id": "identity-uuid",
                    "inbound_labels": ["label1", "label2"],
                }
            ],
            task_id=message_id,
        ).get()

        self.assertEqual(len(responses.calls), 1)


class GetIdentityFromMsisdnTests(TestCase):
    @responses.activate
    def test_get_identity_from_msisdn(self):
        """
        Should add the identity to the specified field in the context
        """
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/"
            "?details__addresses__msisdn=%2B27820001001",
            json={"results": [{"id": "identity-uuid"}]},
        )

        context = get_identity_from_msisdn.delay(
            {"identity_msisdn": "27820001001"}, "identity_msisdn"
        ).get()

        self.assertEqual(
            context, {"identity_msisdn": "27820001001", "identity_id": "identity-uuid"}
        )


class ProcessEngageHelpdeskOutboundTests(DisconnectRegistrationSignalsMixin, TestCase):
    @responses.activate
    def test_process_engage_helpdesk_outbound(self):
        """
        Tests that the workflow combines as expected. This doesn't cover all edge cases,
        the individual task tests are meant to do that. This just covers that the data
        passed from one task to another works.
        """

        message_id = "cdffd588-dc29-469d-b2ac-3a0c2d5d8609"

        responses.add(
            responses.GET,
            "http://engage/v1/contacts/27820001001/messages",
            status=200,
            json={
                "messages": [
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "outbound",
                                "in_reply_to": "gBGGJ3EVEUV_AgkC5c71UQ9ug08",
                                "author": {
                                    "id": "2ab15df1-082a-4420-8f1a-1fed53b13eba",
                                    "name": "Operator Name",
                                    "type": "OPERATOR",
                                },
                                "labels": [],
                            }
                        },
                        "from": "27820001002",
                        "id": message_id,
                        "text": {"body": "Operator answer"},
                        "timestamp": "1540803363",
                        "type": "text",
                    },
                    {
                        "_vnd": {
                            "v1": {
                                "direction": "inbound",
                                "in_reply_to": None,
                                "labels": [
                                    {
                                        "uuid": "cbaf27bc-2ba9-4e4a-84c1-098d5abd80bf",
                                        "value": "test",
                                    }
                                ],
                            }
                        },
                        "from": "27820001001",
                        "id": "ABGGJ3EVEUV_AhALwhRTSopsSmF7IxgeYIBz",
                        "text": {"body": "Mother question"},
                        "timestamp": "1540803293",
                        "type": "text",
                    },
                ]
            },
        )
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/"
            "?details__addresses__msisdn=%2B27820001001",
            json={"results": [{"id": "identity-uuid"}]},
        )

        def assert_openhim_request(request):
            payload = json.loads(request.body)
            self.assertEqual(
                payload,
                {
                    "encdate": "20181029085453",
                    "repdate": "20181029085603",
                    "mha": 1,
                    "swt": 4,
                    "cmsisdn": "+27820001001",
                    "dmsisdn": "+27820001001",
                    "eid": message_id,
                    "sid": "identity-uuid",
                    "faccode": "123456",
                    "data": {
                        "question": "Mother question",
                        "answer": "Operator answer",
                    },
                    "class": "test",
                    "type": 7,
                    "op": "56748517727534413379787391391214157498",
                },
            )
            return (200, {}, json.dumps({}))

        responses.add_callback(
            responses.POST,
            "http://jembi/ws/rest/v1/helpdesk",
            callback=assert_openhim_request,
            content_type="application/json",
        )

        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        Registration.objects.create(
            registrant_id="identity-uuid", data={"faccode": "123456"}, source=source
        )

        process_engage_helpdesk_outbound.apply_async(
            args=["27820001001", message_id], task_id=message_id
        ).get()


class RefreshEngageContextTests(TestCase):
    @responses.activate
    def test_http_request(self):
        """
        Makes the correct HTTP request with the correct parameters to request a refresh
        of the engage context
        """
        responses.add(
            responses.POST,
            "http://engage/api/integrations/8cf3d402-7b25-47fd-8ef2-3e2537fccc14/"
            "notify/finish",
        )
        refresh_engage_context(
            "8cf3d402-7b25-47fd-8ef2-3e2537fccc14",
            "009d3a39-326c-42f3-af72-b5ddbece219a",
        )
        [call] = responses.calls
        self.assertEqual(
            json.loads(call.request.body),
            {"integration_action_uuid": "009d3a39-326c-42f3-af72-b5ddbece219a"},
        )
        self.assertEqual(
            call.request.headers["User-Agent"], "ndoh-hub/{}".format(utils.VERSION)
        )
        self.assertEqual(call.request.headers["Authorization"], "Bearer engage-token")
        self.assertEqual(call.request.headers["Content-Type"], "application/json")
