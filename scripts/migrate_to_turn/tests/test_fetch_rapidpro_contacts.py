import csv
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import pytz

from scripts.migrate_to_turn import fetch_rapidpro_contacts


@contextmanager
def chdir(path):
    current = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)


class FakeContacts:
    def __init__(self, batches):
        self._batches = batches

    def iterfetches(self, retry_on_rate_exceed=False):
        yield from self._batches


class FakeClient:
    def __init__(self, batches):
        self._batches = batches

    def get_contacts(self, before=None, after=None):
        return FakeContacts(self._batches)


class FetchRapidproContactsTests(TestCase):
    def test_fetch_rapidpro_contacts_writes_csv(self):
        contact = type(
            "Contact",
            (),
            {
                "fields": {
                    "edd": "2025-01-02T12:00:00",
                    "research_consent": "TRUE",
                    "clinic_code": "123",
                    "registered_by": "+27123",
                    "education": "secondary",
                    "opted_out": "FALSE",
                    "prebirth_messaging": "1",
                    "postbirth_messaging": "TRUE",
                    "baby_dob1": "2025-02-03",
                    "underage_mother": "Yes",
                    "loss_messaging": "TRUE",
                    "optout_reason": "baby_loss",
                    "preferred_channel": "WHATSAPP",
                },
                "urns": ["whatsapp:27820000000"],
                "modified_on": datetime(2025, 1, 3, 12, 0, 0, tzinfo=pytz.utc),
                "name": "Alice",
                "language": "eng",
            },
        )()

        client = FakeClient([[contact]])
        start_date = "2025-01-01 00:00:00"
        end_date = "2025-01-31 00:00:00"

        with tempfile.TemporaryDirectory() as tmp_dir, chdir(tmp_dir):
            with (
                patch.object(fetch_rapidpro_contacts, "START_DATE", start_date),
                patch.object(fetch_rapidpro_contacts, "END_DATE", end_date),
            ):
                fetch_rapidpro_contacts.fetch_rapidpro_contacts(client)

            output_path = Path(tmp_dir) / "contacts-2025-01-01-2025-01-31.csv"
            with output_path.open(newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)

        expected_headers = [
            "pregnancy_expected_due_date",
            "name",
            "language",
            "research_consent",
            "clinic_code",
            "referred_number",
            "education",
            "opted_in",
            "pregnancy_message_status",
            "baby_message_status",
            "minor_healthcare_consent",
            "opt_out_reason",
            "active_channel",
            "user_type",
            "baby_loss_status",
            "pregnancy_loss_status",
            "is_new_user",
            "babies",
            "urn",
        ]

        self.assertEqual(reader.fieldnames, expected_headers)
        self.assertEqual(len(rows), 1)

        expected_row = {
            "pregnancy_expected_due_date": fetch_rapidpro_contacts.process_datetime(
                contact.fields["edd"]
            ),
            "name": "Alice",
            "language": "eng",
            "research_consent": "true",
            "clinic_code": "123",
            "referred_number": "+27123",
            "education": "secondary",
            "opted_in": "true",
            "pregnancy_message_status": "true",
            "baby_message_status": "true",
            "minor_healthcare_consent": "true",
            "opt_out_reason": "baby_loss",
            "active_channel": "whatsapp",
            "user_type": fetch_rapidpro_contacts.get_user_type(contact) or "",
            "baby_loss_status": "true",
            "pregnancy_loss_status": "",
            "is_new_user": "no",
            "babies": fetch_rapidpro_contacts.get_user_babies(contact),
            "urn": "27820000000",
        }

        self.assertEqual(rows[0], expected_row)
