import datetime
from unittest import mock

from django.test import TestCase
from django.core.exceptions import ValidationError

from registrations import validators


def override_get_today():
    return datetime.date(2016, 1, 1)


class ValidatorsTests(TestCase):
    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_invalid_edd(self):
        """
        If the EDD is greater than 43 weeks from todays date, a validation
        error should be raised
        """
        self.assertRaisesMessage(
            ValidationError,
            "Must be in the future, but less than 43 weeks away",
            validators.edd,
            datetime.date(2016, 12, 1),
        )

    def test_invalid_consent(self):
        """
        If consent is False, it should raise a validation error
        """
        self.assertRaisesMessage(
            ValidationError,
            "Mother must consent for registration",
            validators.consent,
            False,
        )

    def test_invalid_sa_id_no(self):
        """
        If the SA ID number isn't valid, it should raise a validation error
        """
        self.assertRaisesMessage(
            ValidationError, "Invalid SA ID number", validators.sa_id_no, "123"
        )

    def test_invalid_passport_no(self):
        """
        If the passport number is invalid, it should raise a validation error
        """
        self.assertRaisesMessage(
            ValidationError, "Invalid passport number", validators.passport_no, ""
        )

    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_invalid_baby_dob(self):
        """
        If the baby's DoB is in the future, or greater than 2 years from today's date,
        a validation error should be raised
        """
        self.assertRaisesMessage(
            ValidationError,
            "Must be in the past, but less than 2 years old",
            validators.baby_dob,
            datetime.date(2016, 1, 2),
        )

        self.assertRaisesMessage(
            ValidationError,
            "Must be in the past, but less than 2 years old",
            validators.baby_dob,
            datetime.date(2014, 1, 1),
        )

    def test_invalid_geographic_coordinate(self):
        """
        Should raise a validation error for invalid coordinates
        """
        self.assertRaisesMessage(
            ValidationError,
            "Invalid ISO6709 geographic coordinate",
            validators.geographic_coordinate,
            "not-a-coordinate",
        )
