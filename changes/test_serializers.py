from django.test import TestCase

from changes.serializers import ReceiveWhatsAppEventSerializer


class ReceiveWhatsAppEventSerializerTests(TestCase):
    def test_valid(self):
        serializer = ReceiveWhatsAppEventSerializer(data={
            'hook': {
                'event': 'message.direct_outbound.status',
            },
            'data': {
                'id': 12345,
                'message_uuid': '8773bd92-a28a-438d-942b-3b8aca3a216e',
                'contact_uuid': 'f87e5256-f26d-4e96-97b4-ed5e4d462a33',
                'group_uuid': None,
                'message_metadata': {
                    'wassup_reply': {},
                    'junebug_reply_to': None,
                    'junebug_message_id': '41c377a47b064eba9abee5a1ea827b3d',
                },
                'uuid': '8ec6b95a-f43e-4000-8f4d-bf3e359bb3e',
                'status': 'unsent',
                'description': None,
                'timestamp': '2018-04-19T09:36:38Z',
                'created_at': '2018-04-19T09:36:38.842036Z',
                'updated_at': '2018-04-19T09:36:38.842054Z',
                'message': 12346,
                'contact': 12347,
            },
        })

        self.assertTrue(serializer.is_valid())

    def test_invalid_incorrect_event(self):
        """
        If the event is not message.direct_outbound.status, then the serializer
        should be invalid
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            'hook': {
                'event': 'message.direct_outbound',
            },
            'data': {
                'message_metadata': {
                    'junebug_message_id': '41c377a47b064eba9abee5a1ea827b3d',
                },
                'status': 'unsent',
            },
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'hook': {
                'event': ['"message.direct_outbound" is not a valid choice.'],
            },
        })

    def test_invalid_incorrect_status(self):
        """
        If the status is not unsent, then the serializer should be invalid
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            'hook': {
                'event': 'message.direct_outbound.status',
            },
            'data': {
                'message_metadata': {
                    'junebug_message_id': '41c377a47b064eba9abee5a1ea827b3d',
                },
                'status': 'sent',
            },
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'data': {
                'status': ['"sent" is not a valid choice.'],
            },
        })

    def test_invalid_incorrect_junebug_message_id(self):
        """
        junebug_message_id must be present, and must be a valid UUID.
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            'hook': {
                'event': 'message.direct_outbound.status',
            },
            'data': {
                'message_metadata': {
                    'junebug_message_id': 'bad-uuid',
                },
                'status': 'unsent',
            },
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'data': {
                'message_metadata': {
                    'junebug_message_id': ['"bad-uuid" is not a valid UUID.'],
                },
            },
        })
