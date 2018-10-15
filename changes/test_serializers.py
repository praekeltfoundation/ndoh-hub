from django.test import TestCase

from changes.serializers import (
    ReceiveWhatsAppEventSerializer, ReceiveWhatsAppSystemEventSerializer)


class ReceiveWhatsAppEventSerializerTests(TestCase):
    def test_valid(self):
        serializer = ReceiveWhatsAppEventSerializer(data={
            "statuses": [
                {
                    "errors": [
                        {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
                    ],
                    "id": "41c377a47b064eba9abee5a1ea827b3d",
                    "recipient_id": "27831112222",
                    "status": "failed",
                    "timestamp": "1538388353"
                },
                {
                    "errors": [
                        {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
                    ],
                    "id": "kdmfglkdfmlgkdfmgkdmlfkgmdlfkgdm",
                    "recipient_id": "27831114444",
                    "status": "failed",
                    "timestamp": "1538388354"
                }
            ]
        })

        self.assertTrue(serializer.is_valid())

    def test_valid_and_invalid(self):
        serializer = ReceiveWhatsAppEventSerializer(data={
            "statuses": [
                {
                    "errors": [
                        {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
                    ],
                    "id": "41c377a47b064eba9abee5a1ea827b3d",
                    "recipient_id": "27831112222",
                    "status": "failed",
                    "timestamp": "1538388353"
                },
                {
                    "id": "kdmfglkdfmlgkdfmgkdmlfkgmdlfkgdm",
                    "recipient_id": "27831114444",
                    "status": "sent",
                    "timestamp": "1538388354"
                }
            ]
        })

        self.assertTrue(serializer.is_valid())
        statuses = serializer.validated_data["statuses"]
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0]["status"], "failed")

    def test_invalid_incorrect_status(self):
        """
        If the status is not unsent, then the serializer should be invalid
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            "statuses": [
                {
                    "id": "kdmfglkdfmlgkdfmgkdmlfkgmdlfkgdm",
                    "recipient_id": "27831114444",
                    "status": "sending",
                    "timestamp": "1538388354"
                }
            ]
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'statuses':
                ['Ensure this field has at least 1 elements.']
        })

    def test_invalid_missing_message_id(self):
        """
        id must be present.
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            "statuses": [
                {
                    "errors": [
                        {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
                    ],
                    "recipient_id": "27831112222",
                    "status": "failed",
                    "timestamp": "1538388353"
                }
            ]
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'statuses': {
                0: {
                    'id': ['This field is required.']
                }
            }
        })


class ReceiveWhatsAppSystemEventSerializerTests(TestCase):

    def test_valid(self):
        serializer = ReceiveWhatsAppSystemEventSerializer(data={
            "events": [
                {
                    "recipient_id": "27831112222",
                    "timestamp": "1538388353",
                    "message_id": "gBGGJ4NjeFMfAgl58_8Il_tnCNI",
                    "type": "undelivered"
                }, {
                    "recipient_id": "27831113333",
                    "timestamp": "1538388354",
                    "message_id": "gBGGJ4NjeFMfAgl58_8Il_WWWWW",
                    "type": "something_else"
                }
            ]
        })

        self.assertTrue(serializer.is_valid())

    def test_missing_message_id(self):
        serializer = ReceiveWhatsAppSystemEventSerializer(data={
            "events": [
                {
                    "recipient_id": "27831112222",
                    "timestamp": "1538388353",
                    "type": "undelivered"
                }, {
                    "recipient_id": "27831113333",
                    "timestamp": "1538388354",
                    "message_id": "gBGGJ4NjeFMfAgl58_8Il_WWWWW",
                    "type": "undelivered"
                }
            ]
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'events': {
                0: {
                    'message_id': ['This field is required.']
                }
            }
        })
