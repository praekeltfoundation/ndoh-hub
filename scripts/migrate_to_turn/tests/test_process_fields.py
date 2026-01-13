import json
from datetime import datetime
from unittest import TestCase

import pytz

from scripts.migrate_to_turn.process_fields import (
    get_user_babies,
    get_user_tier,
    get_user_type,
    is_datetime,
    process_baby_loss_status,
    process_datetime,
    process_opted_in,
    process_pregnancy_loss_status,
    process_truthy,
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


class ProcessOptedInTests(TestCase):
    def test_none_returns_true(self):
        """
        Defaults to true when value is missing
        """
        self.assertEqual(process_opted_in(None), "true")

    def test_empty_string_returns_true(self):
        """
        Defaults to true for empty strings
        """
        self.assertEqual(process_opted_in(""), "true")

    def test_true_string_returns_false(self):
        """
        Inverts TRUE to false
        """
        for value in ("TRUE", "true", "TrUe"):
            with self.subTest(value=value):
                self.assertEqual(process_opted_in(value), "false")

    def test_false_string_returns_true(self):
        """
        Non-TRUE values stay true
        """
        for value in ("FALSE", "false", "no", "0"):
            with self.subTest(value=value):
                self.assertEqual(process_opted_in(value), "true")

    def test_bool_values(self):
        """
        Boolean values follow string conversion
        """
        self.assertEqual(process_opted_in(True), "false")
        self.assertEqual(process_opted_in(False), "true")


class ProcessTruthyTests(TestCase):
    def test_none_returns_false(self):
        """
        Defaults to false when value is missing
        """
        self.assertEqual(process_truthy(None), "false")

    def test_empty_string_returns_false(self):
        """
        Defaults to false for empty strings
        """
        self.assertEqual(process_truthy(""), "false")

    def test_false_values_return_false(self):
        """
        False-like values return false
        """
        for value in ("FALSE", "false", " False ", "no", "NO", "0", 0, False):
            with self.subTest(value=value):
                self.assertEqual(process_truthy(value), "false")

    def test_non_false_values_return_true(self):
        """
        Non-empty values return true
        """
        for value in ("true", "yes", 1, True):
            with self.subTest(value=value):
                self.assertEqual(process_truthy(value), "true")


class ProcessBabyLossStatusTests(TestCase):
    def test_returns_true_for_baby_loss(self):
        """
        Returns true when loss messaging and baby loss are set
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"loss_messaging": "TRUE", "optout_reason": "baby_loss"}},
        )()

        self.assertEqual(process_baby_loss_status(contact), "true")

    def test_returns_none_for_other_reasons(self):
        """
        Returns None when conditions are not met
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"loss_messaging": "FALSE", "optout_reason": "baby_loss"}},
        )()

        self.assertIsNone(process_baby_loss_status(contact))


class ProcessPregnancyLossStatusTests(TestCase):
    def test_returns_true_for_pregnancy_loss(self):
        """
        Returns true when loss messaging and miscarriage/stillbirth are set
        """
        for reason in ("miscarriage", "stillbirth"):
            with self.subTest(reason=reason):
                contact = type(
                    "Contact",
                    (),
                    {"fields": {"loss_messaging": "TRUE", "optout_reason": reason}},
                )()

                self.assertEqual(process_pregnancy_loss_status(contact), "true")

    def test_returns_none_for_other_reasons(self):
        """
        Returns None when conditions are not met
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"loss_messaging": "TRUE", "optout_reason": "baby_loss"}},
        )()

        self.assertIsNone(process_pregnancy_loss_status(contact))


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
                "all_vaccines_received": "",
                "appointments_attended": 0,
                "baby_birth_day": 2,
                "baby_birth_month": 1,
                "baby_birth_year": 2025,
                "name": "",
                "next_vacc_day": 0,
                "next_vacc_month": 0,
                "next_vacc_year": 0,
                "pregnancy_edd": 0,
                "vaccination_status_at_reg": "",
            }
        ]

        self.assertEqual(get_user_babies(contact), json.dumps(baby_list))
