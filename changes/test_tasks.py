import responses
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.test import TestCase
from unittest import mock


from registrations.models import Source
from changes.models import Change
from changes.signals import psh_validate_implement
from changes.tasks import (
    process_whatsapp_unsent_event, process_whatsapp_system_event)


class WhatsAppBaseTestCase(TestCase):

    def create_outbound_lookup(self, result_count=1):

        results = []
        for i in range(0, result_count):
            results.append({'to_identity': 'test-identity-uuid'})

        responses.add(
            responses.GET,
            'http://ms/api/v1/outbound/?vumi_message_id=messageid',
            json={
                'results': results
            }, status=200, match_querystring=True)

    def create_identity_lookup(self, lang="eng_ZA"):
        responses.add(
            responses.GET,
            'http://is/api/v1/identities/test-identity-uuid/',
            json={
                'identity': 'result',
                'details': {
                    'lang_code': lang
                }
            },
            status=200, match_querystring=True)


class ProcessWhatsAppUnsentEventTaskTests(WhatsAppBaseTestCase):
    def setUp(self):
        post_save.disconnect(
            receiver=psh_validate_implement, sender=Change)

    def tearDown(self):
        post_save.connect(
            receiver=psh_validate_implement, sender=Change)

    @mock.patch('changes.tasks.utils.ms_client.create_outbound')
    @responses.activate
    def test_change_created(self, mock_create_outbound):
        """
        The task should create a Change according to the details received from
        the message sender
        """
        user = User.objects.create_user('test')
        source = Source.objects.create(user=user)

        self.create_outbound_lookup()
        self.create_identity_lookup()

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event('messageid', source.pk, [{
            'code': 500,
            "title": "structure unavailable: Client could not display highly "
                     "structured message"}
        ])

        [change] = Change.objects.all()
        self.assertEqual(change.registrant_id, 'test-identity-uuid')
        self.assertEqual(change.action, 'switch_channel')
        self.assertEqual(change.data, {
            'channel': 'sms',
            'reason': 'whatsapp_unsent_event',
        })
        self.assertEqual(change.created_by, user)

        mock_create_outbound.assert_called_once_with({
            'to_identity': 'test-identity-uuid',
            'content':
                "Sorry, we can't send WhatsApp msgs to this phone. We'll send "
                "your MomConnect msgs on SMS. To stop dial *134*550*1#, for "
                "more dial *134*550*7#.",
            'channel': "JUNE_TEXT",
            'metadata': {},
        })

    @mock.patch('changes.tasks.utils.ms_client.create_outbound')
    @responses.activate
    def test_change_created_diff_language(self, mock_create_outbound):
        """
        The task should create a Change according to the details received from
        the message sender
        """
        user = User.objects.create_user('test')
        source = Source.objects.create(user=user)

        self.create_outbound_lookup()
        self.create_identity_lookup('zul_ZA')

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event('messageid', source.pk, [{
            'code': 500,
            "title": "structure unavailable: Client could not display highly "
                     "structured message"}
        ])

        mock_create_outbound.assert_called_once_with({
            'to_identity': 'test-identity-uuid',
            'content':
                "Siyaxolisa asikwazi ukusenda uWhatsApp kule foni. "
                "Sizokusendela imiyalezo yeMomConnect ngeSMS. Ukuphuma dayela "
                "*134*550*1# Ukuthola okunye dayela *134*550*7#.",
            'channel': "JUNE_TEXT",
            'metadata': {},
        })

    @responses.activate
    def test_no_outbound_message(self):
        """
        If no outbound message can be found, then the change shouldn't be
        created
        """
        user = User.objects.create_user('test')
        source = Source.objects.create(user=user)

        self.create_outbound_lookup(0)

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event('messageid', source.pk, [{
            'code': 500,
            "title": "structure unavailable: Client could not display highly "
                     "structured message"}
        ])

        self.assertEqual(Change.objects.count(), 0)

    @responses.activate
    def test_non_hsm_failure(self):
        """
        The task should not create a switch if it is not a hsm failure
        """
        user = User.objects.create_user('test')
        source = Source.objects.create(user=user)

        self.create_outbound_lookup(1)

        self.assertEqual(Change.objects.count(), 0)

        process_whatsapp_unsent_event('messageid', source.pk, [{
            'code': 200,
            "title": "random error: temporary random error"}
        ])

        self.assertEqual(Change.objects.count(), 0)


class ProcessWhatsAppSystemEventTaskTests(WhatsAppBaseTestCase):

    @mock.patch('changes.tasks.utils.ms_client.create_outbound')
    @responses.activate
    def test_message_sent_delivered(self, mock_create_outbound):
        """
        The task should send the correct outbound based on the delivered event.
        """
        self.create_outbound_lookup()
        self.create_identity_lookup()

        process_whatsapp_system_event('messageid', "undelivered")

        mock_create_outbound.assert_called_once_with({
            'to_identity': 'test-identity-uuid',
            'content':
                "We see that your MomConnect WhatsApp messages are not being "
                "delivered. If you would like to receive your messages over "
                "SMS, reply ‘SMS’.",
            'channel': "JUNE_TEXT",
            'metadata': {},
        })

    @mock.patch('changes.tasks.utils.ms_client.create_outbound')
    @responses.activate
    def test_no_message_sent(self, mock_create_outbound):
        """
        The task should not create a Outbound when the event is the wrong type.
        """
        self.create_outbound_lookup()

        process_whatsapp_system_event('messageid', "something_else")

        self.assertFalse(mock_create_outbound.called)

    @mock.patch('changes.tasks.utils.ms_client.create_outbound')
    @responses.activate
    def test_no_message_found(self, mock_create_outbound):
        """
        The task should not create a outbound if the original message was not
        found
        """
        self.create_outbound_lookup(0)

        process_whatsapp_system_event('messageid', "something_else")

        self.assertFalse(mock_create_outbound.called)
