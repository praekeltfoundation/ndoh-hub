from django.core.exceptions import ValidationError
from django.test import TestCase

from eventstore.validators import validate_sa_id_number


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
