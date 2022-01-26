from unittest import TestCase

import phonenumbers
from rest_framework.serializers import ValidationError

from registrations.fields import PhoneNumberField


class PhoneNumberFieldTests(TestCase):
    def test_valid_number(self):
        """
        If a valid phone number is supplied, then a valid PhoneNumber should be
        returned.
        """
        number = PhoneNumberField().to_internal_value("+27820001001")
        self.assertEqual(number.country_code, 27)
        self.assertEqual(number.national_number, 820001001)

    def test_country_code(self):
        """
        If a country code is supplied, it should be used when interpreting the
        number.
        """
        number = PhoneNumberField(country_code="ZA").to_internal_value("0820001001")
        self.assertEqual(number.country_code, 27)

    def test_cannot_parse(self):
        """
        If the supplied data cannot be parsed as a phone number, a validation
        exception should be raised
        """
        with self.assertRaises(ValidationError) as e:
            PhoneNumberField().to_internal_value("bad")
        self.assertIn("Cannot parse", str(e.exception))

    def test_not_possible_number(self):
        """
        If the supplied number is not possible, a validation exception should
        be raised
        """
        with self.assertRaises(ValidationError) as e:
            PhoneNumberField().to_internal_value("+120012301")
        self.assertIn("Not a possible phone number", str(e.exception))

    def test_not_valid_phone_number(self):
        """
        If the supplied number is not valid, a validation exception should be
        raised
        """
        with self.assertRaises(ValidationError) as e:
            PhoneNumberField().to_internal_value("+12001230101")
        self.assertIn("Not a valid phone number", str(e.exception))

    def test_to_representation(self):
        """
        The phone number should be in E164 format for representation
        """
        number = phonenumbers.parse("0820001001", "ZA")
        self.assertEqual(PhoneNumberField().to_representation(number), "+27820001001")
