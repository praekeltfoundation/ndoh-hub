from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from eventstore.forms import MomConnectImportForm
from eventstore.models import ImportRow, MomConnectImport
from registrations.models import ClinicCode


class MomConnectImportFormTests(TestCase):
    def setUp(self):
        ClinicCode.objects.create(value="123456")
        patcher = mock.patch("eventstore.models.is_valid_edd_date")
        self.is_valid_edd_date = patcher.start()
        self.is_valid_edd_date.return_value = True
        patcher = mock.patch("eventstore.forms.validate_momconnect_import")
        self.validate_momconnect_import = patcher.start()

    def tearDown(self):
        self.is_valid_edd_date.stop()
        self.validate_momconnect_import.stop()

    def test_missing_columns(self):
        """
        Should mark the import as error, and write an error for the missing columns
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,messaging consent,edd year,edd month,baby dob year,"
            b"baby dob month,baby dob day\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
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
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
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
            b"edd month,edd day,baby dob year, baby dob month, baby dob day,language\n"
            b"+27820001001,123456,said,9001010001088,true,2021,12,1,,,,afr\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
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
        self.assertEqual(row.messaging_consent, True)
        self.assertEqual(row.research_consent, False)
        self.assertEqual(row.edd_year, 2021)
        self.assertEqual(row.edd_month, 12)
        self.assertEqual(row.edd_day, 1)
        self.assertEqual(row.language, ImportRow.Language.AFR)

        self.validate_momconnect_import.delay.assert_called_once_with(instance.id)

    def test_empty_language(self):
        """
        Should save the rows
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day,language\n"
            b"+27820001001,123456,said,9001010001088,true,2021,12,1,,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.VALIDATING)
        self.assertEqual(instance.errors.count(), 0)

        [row] = instance.rows.all()
        self.assertEqual(row.language, ImportRow.Language.ENG)

        self.validate_momconnect_import.delay.assert_called_once_with(instance.id)

    def test_invalid_msisdn(self):
        """
        Should mark import as error, and write an error row
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+1234,123456,said,9001010001088,1,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field msisdn failed validation: Not a possible phone number"
        )
        self.assertEqual(error.row_number, 2)

    def test_invalid_messaging_consent(self):
        """
        messaging_consent should be present and be True
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field messaging_consent failed validation: This field is required.",
        )
        self.assertEqual(error.row_number, 2)

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,no,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field messaging_consent failed validation: False is not true"
        )
        self.assertEqual(error.row_number, 2)

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,foo,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field messaging_consent failed validation: “foo” value must be either "
            "True or False.",
        )
        self.assertEqual(error.row_number, 2)

    def test_invalid_research_consent(self):
        """
        research_consent should have a valid value
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"research_consent,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,foo,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field research_consent failed validation: “foo” value must be either "
            "True or False.",
        )
        self.assertEqual(error.row_number, 2)

    def test_research_consent_default(self):
        """
        research_consent should default to False
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"research_consent,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.VALIDATING)
        self.assertEqual(instance.errors.count(), 0)
        [row] = instance.rows.all()
        self.assertFalse(row.research_consent)

    def test_invalid_previous_optout(self):
        """
        previous_optout should have a valid value
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"previous_optout,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,foo,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field previous_optout failed validation: “foo” value must be either "
            "True or False.",
        )
        self.assertEqual(error.row_number, 2)

    def test_previous_optout_default(self):
        """
        previous_optout should default to True
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"previous_optout,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.VALIDATING)
        self.assertEqual(instance.errors.count(), 0)
        [row] = instance.rows.all()
        self.assertTrue(row.previous_optout)

    def test_facility_code_invalid(self):
        """
        facility_code must be in the database
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,,said,9001010001088,true,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field facility_code failed validation: This field is required.",
        )

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,abc123,said,9001010001088,true,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field facility_code failed validation: Invalid Facility Code"
        )

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,1234567,said,9001010001088,true,2021,12,1,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field facility_code failed validation: Ensure this value has at most 6 "
            "characters (it has 7).",
        )

    def test_invalid_edd(self):
        """
        edd fields should form a valid date, that is between now and 9 months from now
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,2021,2,29,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Failed validation: Invalid EDD date, day is out of range for month",
        )

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,2021,Feb,20,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field edd_month failed validation: Enter a whole number."
        )

        self.is_valid_edd_date.return_value = False
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,2121,2,4,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Failed validation: EDD must be between now and 9 months"
        )

    def test_invalid_baby_dob(self):
        """
        baby dob fields should form a valid date
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,,,,2021,2,29\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Failed validation: Invalid Baby DOB date, day is out of range for month",
        )

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,,,,2021,Feb,20\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Field baby_dob_month failed validation: Enter a whole number."
        )

    def test_valid_baby_dob_or_edd(self):
        """
        baby dob or edd should be added
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,"
            b"edd year,edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001088,true,,,,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Failed validation: EDD or Baby DOB fields must be populated"
        )

    def test_idtype_said(self):
        """
        id_number is required for sa_id
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,messaging consent,edd year,edd month,"
            b"edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,true,2021,2,3,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Failed validation: ID number required for SA ID ID type"
        )

    def test_invalid_id_number(self):
        """
        id number must be valid
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,id number,messaging consent,edd year,"
            b"edd month,edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,said,9001010001089,true,2021,2,3,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Field id_number failed validation: Invalid ID number: "
            "Failed Luhn checksum",
        )

    def test_idtype_passport(self):
        """
        passport country and passport number are required for passport
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,passport number,passport country,"
            b"messaging consent,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,passport,A1234,,true,2021,2,3,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Failed validation: Passport country required for passport ID type",
        )

        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,passport number,passport country,"
            b"messaging consent,edd year,edd month,edd day,baby dob year,"
            b"baby dob month,baby dob day\n"
            b"+27820001001,123456,passport,,zimbabwe,true,2021,2,3,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Failed validation: Passport number required for passport ID type",
        )

    def test_idtype_dob(self):
        """
        dob is required for none id type
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,messaging consent,edd year,edd month,"
            b"edd day,baby dob year,baby dob month,baby dob day\n"
            b"+27820001001,123456,none,true,2021,2,3,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error, "Failed validation: Date of birth required for none ID type"
        )

    def test_invalid_dob(self):
        """
        dob should be a valid date
        """
        file = SimpleUploadedFile(
            "test.csv",
            b"msisdn,facility code,id type,messaging consent,edd year,edd month,"
            b"edd day,dob year,dob month,dob day,baby dob year,baby dob month,"
            b"baby dob day\n"
            b"+27820001001,123456,none,true,2021,2,3,1990,2,29,,,\n",
        )
        form = MomConnectImportForm(
            data={"source": "MomConnect Import"}, files={"file": file}
        )
        instance = form.save()
        self.assertEqual(instance.status, MomConnectImport.Status.ERROR)
        [error] = instance.errors.all()
        self.assertEqual(
            error.error,
            "Failed validation: Invalid date of birth date, day is out of range for "
            "month",
        )
