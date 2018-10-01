from django.test import TestCase

from changes.serializers import ReceiveWhatsAppEventSerializer


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

    def test_invalid_incorrect_status(self):
        """
        If the status is not unsent, then the serializer should be invalid
        """
        serializer = ReceiveWhatsAppEventSerializer(data={
            "statuses": [
                {
                    "id": "kdmfglkdfmlgkdfmgkdmlfkgmdlfkgdm",
                    "recipient_id": "27831114444",
                    "status": "sent",
                    "timestamp": "1538388354"
                }
            ]
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'statuses': {
                'status': ['"sent" is not a valid choice.'],
            },
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
                'id': ['This field is required.']
            }
        })
