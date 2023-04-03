from django.test import TestCase, override_settings

from eventstore.batch_tasks import bulk_insert_events
from eventstore.models import DeliveryFailure, Event


class UpdateTurnContactTaskTest(TestCase):
    @override_settings(ENABLE_EVENTSTORE_WHATSAPP_ACTIONS=True)
    def test_batch_insert_events(self):
        DeliveryFailure.objects.get_or_create(
            contact_id="recipient_id", defaults={"number_of_failures": 0}
        )

        bulk_insert_events.delay(
            message_id="message_id",
            recipient_id="recipient_id",
            timestamp="2023-10-11 12:33",
            status="failed",
            created_by="test user",
            data={},
            fallback_channel=False,
        )

        [event] = Event.objects.all()

        self.assertEqual("message_id", event.message_id)
        self.assertEqual("recipient_id", event.recipient_id)
        self.assertEqual("failed", event.status)
