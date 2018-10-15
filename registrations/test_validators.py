import datetime
from unittest import mock

from django.test import TestCase
from rest_framework.validators import ValidationError

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
