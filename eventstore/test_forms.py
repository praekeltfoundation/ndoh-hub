from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from eventstore.forms import MomConnectImportForm
from eventstore.models import MomConnectImport


class MomConnectImportFormTests(TestCase):
    def test_missing_columns(self):
        """
        Should mark the import as error, and write an error for the missing columns
        """
        file = SimpleUploadedFile(
            "test.csv", b"msisdn,messaging-consent,edd-year,edd-month\n"
        )
        form = MomConnectImportForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Fields edd-day facility-code id-type not found in header"
        )

    def test_invalid_file_type(self):
        """
        If we cannot decode the file, should mark import as error and write an error
        """
        file = SimpleUploadedFile("test.csv", b"\xe8")
        form = MomConnectImportForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(error.error, "File is not a CSV")
