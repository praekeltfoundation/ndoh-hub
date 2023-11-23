from django.core.exceptions import ValidationError
from django.test import TestCase

from eventstore.validators import validate_facility_code, validate_sa_id_number
from registrations.models import ClinicCode


class SAIDNumberTests(TestCase):
    def test_valid(self):
        validate_sa_id_number("9001010001088")

    def test_invalid_format(self):
        self.assertRaisesMessage(
            ValidationError, "Invalid ID number format", validate_sa_id_number, "123"
        )

    def test_invalid_date(self):
        self.assertRaisesMessage(
            ValidationError,
            "Invalid ID number date: day is out of range for month",
            validate_sa_id_number,
            "9002300001088",
        )

    def test_invalid_male(self):
        self.assertRaisesMessage(
            ValidationError,
            "Invalid ID number: for male",
            validate_sa_id_number,
            "9001015001088",
        )

    def test_invalid_luhn(self):
        self.assertRaisesMessage(
            ValidationError,
            "Invalid ID number: Failed Luhn checksum",
            validate_sa_id_number,
            "9001010001089",
        )


class FacilityCodeTests(TestCase):
    def test_valid(self):
        """
        If the facility code exists in the database, should pass
        """
        ClinicCode.objects.create(value="123456")
        validate_facility_code("123456")

    def test_invalid(self):
        """
        If the facility code is not in the database, should fail
        """
        self.assertRaisesMessage(
            ValidationError, "Invalid Facility Code", validate_facility_code, "654321"
        )
