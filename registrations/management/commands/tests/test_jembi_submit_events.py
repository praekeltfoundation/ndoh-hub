from datetime import datetime
from unittest.mock import patch

import pytz
from django.core.management import call_command
from django.test import TestCase

from registrations.models import JembiSubmission


class JembiSubmitEventsTests(TestCase):
    @patch("registrations.management.commands.jembi_submit_events.push_to_jembi_api")
    def test_since_filter(self, task):
        """
        Should not submit any events before the "since" date
        """
        s = JembiSubmission.objects.create(request_data={})
        s.timestamp = datetime(2016, 1, 1, tzinfo=pytz.UTC)
        s.save()
        call_command(
            "jembi_submit_events", since=datetime(2016, 1, 2), submit=True, all=True
        )
        task.delay.assert_not_called()

    @patch("registrations.management.commands.jembi_submit_events.push_to_jembi_api")
    def test_until_filter(self, task):
        """
        Should not submit any events after the "until" date
        """
        s = JembiSubmission.objects.create(request_data={})
        s.timestamp = datetime(2016, 1, 2, tzinfo=pytz.UTC)
        s.save()
        call_command(
            "jembi_submit_events", until=datetime(2016, 1, 1), submit=True, all=True
        )
        task.delay.assert_not_called()

    @patch("registrations.management.commands.jembi_submit_events.push_to_jembi_api")
    def test_all_filter(self, task):
        """
        Should not submit already submitted events if "--all" is not specified
        """
        JembiSubmission.objects.create(request_data={}, submitted=True)
        call_command("jembi_submit_events", submit=True, all=False)
        task.delay.assert_not_called()

    @patch("registrations.management.commands.jembi_submit_events.push_to_jembi_api")
    def test_submit_filter(self, task):
        """
        If submit isn't specified, then we should not submit the events
        """
        JembiSubmission.objects.create(request_data={})
        call_command("jembi_submit_events")
        task.delay.assert_not_called()

    @patch("registrations.management.commands.jembi_submit_events.push_to_jembi_api")
    def test_submit_event(self, task):
        """
        If the event should be submitted, then we should submit it
        """
        s = JembiSubmission.objects.create(path="test", request_data={"test": "data"})
        call_command("jembi_submit_events", submit=True)
        task.delay.assert_called_once_with((s.id, "test", {"test": "data"}))
