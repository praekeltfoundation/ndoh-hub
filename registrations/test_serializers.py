import datetime
from django.test import TestCase
import mock
import pytz
from rest_framework.serializers import ValidationError

from registrations.serializers import (
    MSISDNField, JembiAppRegistrationSerializer)


class MSISDNFieldTests(TestCase):
    def test_internal_value(self):
        """
        A phone number sent to the field should be formatted in E164 format
        """
        field = MSISDNField(country='ZA')
        self.assertEqual(
            field.run_validation('0821234567'), '+27821234567')

    def test_bad_input(self):
        """
        If the input cannot be parsed, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            'The string supplied did not seem to be a phone number',
            field.run_validation, '1')

    def test_impossible_phone_number(self):
        """
        If a phone number is not possible, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            'Not a possible phone number',
            field.run_validation, '+120012301')

    def test_invalid_phone_number(self):
        """
        If a phone number is not valid, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            'Not a valid phone number',
            field.run_validation, '+12001230101')

    def test_representation(self):
        """
        The representation should be in E164
        """
        field = MSISDNField(country='ZA')
        self.assertEqual(
            field.to_representation('0821234567'), '+27821234567')
