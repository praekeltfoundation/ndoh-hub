from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from eventstore.forms import MomConnectImportForm
from eventstore.models import ImportRow, MomConnectImport


class MomConnectImportFormTests(TestCase):
    def test_missing_columns(self):
        """
        Should mark the import as error, and write an error for the missing columns
        """
        file = SimpleUploadedFile(
            "test.csv", b"msisdn,messaging consent,edd year,edd month\n"
        )
        form = MomConnectImportForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Fields edd_day facility_code id_type not found in header"
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

    def test_valid_rows(self):
        """
        Should save the rows
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day\n"
            b"+27820001001,123456,said,9001010001088,false,2021,12,1\n",
        )
        form = MomConnectImportForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.VALIDATING)
        self.assertEqual(instance.errors.count(), 0)

        [row] = instance.rows.all()
        self.assertEqual(row.row_number, 2)
        self.assertEqual(row.msisdn, "+27820001001")
        self.assertEqual(row.facility_code, "123456")
        self.assertEqual(row.id_type, ImportRow.IDType.SAID)
        self.assertEqual(row.id_number, "9001010001088")
        self.assertEqual(row.messaging_consent, False)
        self.assertEqual(row.edd_year, 2021)
        self.assertEqual(row.edd_month, 12)
        self.assertEqual(row.edd_day, 1)

    def test_invalid_msisdn(self):
        """
        Should mark import as error, and write an error row
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day\n"
            b"+1234,123456,said,9001010001088,false,2021,12,1\n",
        )
        form = MomConnectImportForm(data={}, files={"file": file})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field msisdn failed validation: Not a possible phone number"
        )
        self.assertEqual(error.row_number, 2)
