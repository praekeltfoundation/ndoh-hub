import io
import random
import string
import tempfile
import uuid
from urllib.parse import urlencode

import responses
from django.core.management.base import CommandError
from django.test import TestCase
from openpyxl import Workbook

from registrations.management.commands.teenmomconnect_postbirth_subscriptions import (
    Command,
    Contact,
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

    def test_validate_msisdn(self):
        """
        If the msisdn is valid, it should be returned in E164 international format
        """
        command = Command()
        self.assertEqual(command.validate_msisdn("0820001001"), "+27820001001")

    def test_validate_msisdn_not_parsable(self):
        """
        If it's not a parsable msisdn, an error should be logged and `None` should be
        returned
        """
        command = Command()
        command.stdout = io.StringIO()
        self.assertEqual(command.validate_msisdn("gibberish"), None)
        self.assertIn(
            "Invalid phone number gibberish. Skipping...", command.stdout.getvalue()
        )

    def test_validate_msisdn_not_possible(self):
        """
        If it's not a possible msisdn, an error should be logged and `None` should be
        returned
        """
        command = Command()
        command.stdout = io.StringIO()
        self.assertEqual(command.validate_msisdn("+1200012301"), None)
        self.assertIn(
            "Invalid phone number +1200012301. Skipping...", command.stdout.getvalue()
        )

    def test_validate_msisdn_not_valid(self):
        """
        If it's not a valid msisdn, an error should be logged and `None` should be
        returned
        """
        command = Command()
        command.stdout = io.StringIO()
        self.assertEqual(command.validate_msisdn("+12001230101"), None)
        self.assertIn(
            "Invalid phone number +12001230101. Skipping...", command.stdout.getvalue()
        )

    def test_validate_language(self):
        """
        If the language code is valid, it should be returned in the Seed language format
        """
        command = Command()
        self.assertEqual(command.validate_language("eng"), "eng_ZA")

    def test_validate_language_invalid(self):
        """
        If the language code is invalid, an error should be logged and None returned
        """
        command = Command()
        command.stdout = io.StringIO()
        self.assertEqual(command.validate_language("foo"), None)
        self.assertIn(
            "Invalid language code foo. Skipping...", command.stdout.getvalue()
        )

    def test_validate_language_not_in_seed(self):
        """
        If the language code is not in the project's list of languages, an error should
        be logged and None returned
        """
        command = Command()
        command.stdout = io.StringIO()
        self.assertEqual(command.validate_language("arg"), None)
        self.assertIn(
            "Invalid language code arg. Skipping...", command.stdout.getvalue()
        )

    @responses.activate
    def test_create_or_update_identity_exists(self):
        """
        If the identity exists, and the language code is correct, it should be returned
        """
        identity_details = {
            "lang_code": "eng_ZA",
            "default_addr_type": "msisdn",
            "addresses": {
                "msisdn": {"+27820001001": {"default": True, "optedout": False}}
            },
        }
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": [{"id": "identity-uuid", "details": identity_details}]},
        )
        identity = Command.create_or_update_identity("+27820001001", "eng_ZA")
        self.assertEqual(identity, {"id": "identity-uuid", "details": identity_details})
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_create_or_update_identity_does_not_exist(self):
        """
        If the identity does not exist, it should be created
        """
        identity_details = {
            "lang_code": "eng_ZA",
            "default_addr_type": "msisdn",
            "addresses": {
                "msisdn": {"+27820001001": {"default": True, "optedout": False}}
            },
        }
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={"results": []},
        )
        responses.add(
            responses.POST,
            "http://is/api/v1/identities/",
            json={"id": "identity-uuid", "details": identity_details},
        )
        identity = Command.create_or_update_identity("+27820001001", "eng_ZA")
        self.assertEqual(identity, {"id": "identity-uuid", "details": identity_details})
        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_create_or_update_identity_language_incorrect(self):
        """
        If the identity does not have a language, or an incorrect language, it should
        be updated
        """
        identity_details = {
            "lang_code": "eng_ZA",
            "default_addr_type": "msisdn",
            "addresses": {
                "msisdn": {"+27820001001": {"default": True, "optedout": False}}
            },
        }
        identity_details_incorrect_lang = identity_details.copy()
        identity_details_incorrect_lang["lang_code"] = "afr_ZA"
        responses.add(
            responses.GET,
            "http://is/api/v1/identities/search/?{}".format(
                urlencode({"details__addresses__msisdn": "+27820001001"})
            ),
            json={
                "results": [
                    {"id": "identity-uuid", "details": identity_details_incorrect_lang}
                ]
            },
        )
        responses.add(
            responses.PATCH,
            "http://is/api/v1/identities/identity-uuid/",
            json={"id": "identity-uuid", "details": identity_details},
        )
        identity = Command.create_or_update_identity("+27820001001", "eng_ZA")
        self.assertEqual(identity, {"id": "identity-uuid", "details": identity_details})
        self.assertEqual(len(responses.calls), 2)
