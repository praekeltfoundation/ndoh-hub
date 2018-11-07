import random
import tempfile
import string
import uuid

from django.core.management.base import CommandError
from django.test import TestCase
from openpyxl import Workbook

from registrations.management.commands.teenmomconnect_postbirth_subscriptions import (
    Contact,
    Command,
)


def randomword(length):
    """Returns a random string of ascii letters of length `length`"""
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


class TeenMomConnectPostbirthSubscriptionsCommandTests(TestCase):
    @classmethod
    def generate_workbook(cls, contacts):
        """
        Generates a workbook with the specified `contacts`. Returns the file handler
        of the file where the workbook is stored
        """
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet()
        worksheet.append(["Contact UUID", "Name", "Language", "Phone", "Random"])
        for c in contacts:
            worksheet.append(
                [
                    str(uuid.uuid4()),
                    randomword(10),
                    c.language,
                    c.msisdn,
                    randomword(10),
                ]
            )

        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        workbook.save(f.name)
        return f

    def test_extract_contacts_from_workbook(self):
        """
        If the workbook is valid, an iterable of Contacts should be returned.
        """
        contacts = [Contact("+27820001001", "eng"), Contact("+27820001002", "xho")]
        f = self.generate_workbook(contacts)
        extracted_contacts = Command.extract_contacts_from_workbook(f.name)
        self.assertEqual(list(extracted_contacts), contacts)

    def test_extract_contacts_from_workbook_multiple_sheets(self):
        """
        If there is more than one sheet in the workbook, then a CommandError should
        be raised
        """
        workbook = Workbook(write_only=True)
        for _ in range(2):
            workbook.create_sheet()
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        workbook.save(f.name)
        with self.assertRaises(CommandError) as e:
            list(Command.extract_contacts_from_workbook(f.name))
        self.assertIn("Document can only have a single sheet", str(e.exception))

    def test_extract_contacts_from_workbook_no_phone_header(self):
        """
        If there is no `Phone` header field, then a CommandError should be raised
        """
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet()
        worksheet.append(["Contact UUID", "Name", "Language", "Random"])
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        workbook.save(f.name)
        with self.assertRaises(CommandError) as e:
            list(Command.extract_contacts_from_workbook(f.name))
        self.assertIn(
            "Sheet must have a single 'Phone' column header", str(e.exception)
        )

    def test_extract_contacts_from_workbook_no_language_header(self):
        """
        If there is no `Phone` header field, then a CommandError should be raised
        """
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet()
        worksheet.append(["Contact UUID", "Name", "Phone", "Random"])
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        workbook.save(f.name)
        with self.assertRaises(CommandError) as e:
            list(Command.extract_contacts_from_workbook(f.name))
        self.assertIn(
            "Sheet must have a single 'Language' column header", str(e.exception)
        )

    def test_extract_contacts_from_workbook_no_header(self):
        """
        If there is no header field, then a CommandError should be raised
        """
        workbook = Workbook(write_only=True)
        workbook.create_sheet()
        f = tempfile.NamedTemporaryFile(suffix=".xlsx")
        workbook.save(f.name)
        with self.assertRaises(CommandError) as e:
            list(Command.extract_contacts_from_workbook(f.name))
        self.assertIn(
            "Sheet must have a single 'Phone' column header", str(e.exception)
        )
