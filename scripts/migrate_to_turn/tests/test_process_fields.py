import json
from datetime import datetime
from unittest import TestCase

import pytz

from scripts.migrate_to_turn.process_fields import (
    get_user_babies,
    get_user_tier,
    get_user_type,
    is_datetime,
    process_datetime,
)


class IsDatetimeTests(TestCase):
    def test_valid_isoformat(self):
        """
        Returns True for valid ISO format strings
        """
        self.assertTrue(is_datetime("2024-01-01"))
        self.assertTrue(is_datetime("2024-01-01T12:30:00"))

    def test_invalid_isoformat(self):
        """
        Returns False for invalid inputs
        """
        self.assertFalse(is_datetime("not-a-date"))
        self.assertFalse(is_datetime(None))


class ProcessDatetimeTests(TestCase):
    def test_none_returns_none(self):
        """
        Returns None for empty values
        """
        self.assertIsNone(process_datetime(None))
        self.assertIsNone(process_datetime(""))

    def test_invalid_returns_none(self):
        """
        Returns None for invalid values
        """
        self.assertIsNone(process_datetime("not-a-date"))

    def test_strips_timezone_and_converts_to_utc(self):
        """
        Removes timezone suffixes and normalizes to UTC
        """
        for value in ("2024-01-01T12:30:00Z", "2024-01-01T12:30:00+02:00"):
            with self.subTest(value=value):
                expected = datetime.fromisoformat("2024-01-01T12:30:00").astimezone(
                    pytz.utc
                )
                self.assertEqual(process_datetime(value), expected.isoformat())


class GetUserTierTests(TestCase):
    def test_default(self):
        """
        Default behavior returns None
        """
        self.assertIsNone(get_user_tier(object()))


class GetUserTypeTests(TestCase):
    def test_default(self):
        """
        Default behavior returns None
        """
        self.assertIsNone(get_user_type(object()))


class GetUserBabiesTests(TestCase):
    def test_default(self):
        """
        Default behavior returns None
        """
        self.assertIsNone(get_user_babies(object()))

    def test_baby_dobs_convert_to_babies(self):
        """
        Converts baby dob fields into babies payload
        """
        contact = type("Contact", (), {"fields": {"baby_dob1": "2025-01-02"}})()

        baby_list = [
            {
                "all_vaccines_received": "all",
                "appointments_attended": 0,
                "baby_birth_day": 2,
                "baby_birth_month": 1,
                "baby_birth_year": 2025,
                "name": "",
                "next_vacc_day": 0,
                "next_vacc_month": 0,
                "next_vacc_year": 0,
                "pregnancy_edd": 0,
                "vaccination_status_at_reg": "all",
            }
        ]

        self.assertEqual(get_user_babies(contact), json.dumps(baby_list))
