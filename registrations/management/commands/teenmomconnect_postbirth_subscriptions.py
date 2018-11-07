from collections import namedtuple
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook


Contact = namedtuple("Contact", ["msisdn", "language"])


class Command(BaseCommand):
    help = (
        "Creates post birth subscriptions for the mothers specified in the xlsx file. "
        "Doesn't create duplicate subscriptions for mothers that already have a "
        "postbirth subscription"
    )

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="The path to the xlsx file")

    @staticmethod
    def extract_contacts_from_workbook(file_path):
        """
        Extracts the list of Contacts from the workbook at `file_path`, raising a
        CommandError if there are any issues with the workbook's format
        """
        workbook = load_workbook(file_path, read_only=True)

        try:
            [worksheet] = workbook.worksheets
        except ValueError:
            raise CommandError("Document can only have a single sheet")

        try:
            [phone_header] = filter(lambda r: r.value == "Phone", worksheet[1])
        except (ValueError, IndexError):
            raise CommandError("Sheet must have a single 'Phone' column header")
        try:
            [language_header] = filter(lambda r: r.value == "Language", worksheet[1])
        except (ValueError, IndexError):
            raise CommandError("Sheet must have a single 'Language' column header")

        for row in worksheet.iter_rows(min_row=2):
            yield Contact(
                row[phone_header.column - 1].value,
                row[language_header.column - 1].value,
            )

    @staticmethod
    def validate_msisdn(msisdn):
        """
        Returns an E164 internationally formatted msisdn string if valid, else logs an
        error and returns `None`
        """

    @staticmethod
    def create_or_get_identity(msisdn):
        """
        Fetches the identity with the given msisdn, or if identity doesn't exist,
        creates and returns it.
        """

    @staticmethod
    def create_subscription(identity, messageset):
        """
        Creates a subscription to `messageset` for `identity` if such a subscription
        does not yet exist.
        """

    def handle(self, *args, **options):
        contacts = self.extract_contacts_from_workbook(options["file_path"])
        print(list(contacts))
