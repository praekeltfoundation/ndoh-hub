from django.test import TestCase

from eventstore.batch_tasks import bulk_insert_events
from eventstore.models import Event


class UpdateTurnContactTaskTest(TestCase):
    def test_batch_insert_events(self):
        bulk_insert_events.delay(
            message_id="message_id",
            recipient_id="recipient_id",
            timestamp="2023-10-11 12:33",
            status="sent",
            created_by="test user",
            data={},
            fallback_channel=False,
        )

        [event] = Event.objects.all()

        self.assertEqual("message_id", event.message_id)
        self.assertEqual("recipient_id", event.recipient_id)
        self.assertEqual("sent", event.status)
