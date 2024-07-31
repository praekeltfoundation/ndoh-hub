from io import StringIO

from dateutil.relativedelta import relativedelta
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from eventstore.models import Event, Message


class DeleteHistoricalRecordsTests(TestCase):
    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "delete_historical_records",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def create_record(self, model, id, timestamp):
        record = model.objects.create(id=id)
        record.timestamp = timestamp
        record.save()

    def test_missing_arguments(self):
        self.assertRaises(CommandError, self.call_command)

    def test_invalid_arguments(self):
        self.assertRaises(Exception, self.call_command, "InvalidModel")

    def test_delete_events(self):
        running_month = timezone.now() - relativedelta(days=365, hour=12)

        for i in range(12):
            self.create_record(Event, i, running_month)
            running_month = running_month + relativedelta(days=31)

        self.call_command("Event", 6)

        self.assertEqual(Event.objects.count(), 6)

    def test_delete_messages(self):
        running_month = timezone.now() - relativedelta(days=365, hour=12)
        
        for i in range(12):
            self.create_record(Message, i, running_month)
            running_month = running_month + relativedelta(days=31)
            print(f" running month: {running_month}")

        self.call_command("Message", 6)

        self.assertEqual(Message.objects.count(), 6)
