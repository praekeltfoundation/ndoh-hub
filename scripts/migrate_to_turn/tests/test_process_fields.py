import json
from datetime import datetime
from unittest import TestCase, mock

import pytz

from scripts.migrate_to_turn.process_fields import (
    get_pregnancy_in_weeks,
    get_user_babies,
    get_user_dob_year,
    get_user_type,
    get_youngest_dob,
    has_active_baby,
    has_active_baby_between_1_and_2,
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

    def test_import_as_opted_out_forces_false(self):
        """
        Import override always sets opted_in to false
        """
        for value in (None, "", "FALSE", "TRUE", False, True):
            with self.subTest(value=value):
                self.assertEqual(process_opted_in(value, True), "false")


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


class GetUserDobYearTests(TestCase):
    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_rough_dob_year_for_valid_age(self, datetime_mock):
        datetime_mock.now.return_value = datetime(2026, 2, 26, tzinfo=pytz.utc)
        self.assertEqual(get_user_dob_year("25"), 2001)

    def test_returns_empty_string_for_invalid_age(self):
        self.assertEqual(get_user_dob_year("not-a-number"), "")
        self.assertEqual(get_user_dob_year(None), "")

    def test_returns_empty_string_for_negative_age(self):
        self.assertEqual(get_user_dob_year("-1"), "")


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


class GetUserTypeTests(TestCase):
    def test_defaults_to_lead(self):
        """
        Defaults to lead when no flags are set
        """
        contact = type("Contact", (), {"fields": {}})()
        self.assertEqual(get_user_type(contact), "lead")

    def test_opted_out_is_deregistered(self):
        """
        Opted out users are deregistered
        """
        contact = type("Contact", (), {"fields": {"opted_out": "TRUE"}})()
        self.assertEqual(get_user_type(contact), "deregistered_user")

    def test_opted_out_takes_priority_over_all_other_flags(self):
        """
        Opted out should always win regardless of other state
        """
        contact = type(
            "Contact",
            (),
            {
                "fields": {
                    "opted_out": "TRUE",
                    "supporter": "TRUE",
                    "supp_status": "registered",
                    "prebirth_messaging": "TRUE",
                    "postbirth_messaging": "TRUE",
                    "public_messaging": "TRUE",
                }
            },
        )()
        self.assertEqual(get_user_type(contact), "deregistered_user")

    def test_prebirth_messaging_is_comprehensive(self):
        """
        Prebirth messaging users are comprehensive
        """
        contact = type("Contact", (), {"fields": {"prebirth_messaging": "TRUE"}})()
        self.assertEqual(get_user_type(contact), "comprehensive_user")

    def test_postbirth_with_active_baby_is_comprehensive(self):
        """
        Postbirth users with active baby are comprehensive
        """
        contact = type("Contact", (), {"fields": {"postbirth_messaging": "TRUE"}})()
        with mock.patch(
            "scripts.migrate_to_turn.process_fields.has_active_baby", return_value=True
        ):
            self.assertEqual(get_user_type(contact), "comprehensive_user")

    def test_postbirth_without_active_baby_is_alumni(self):
        """
        Postbirth users without active baby are alumni
        """
        contact = type("Contact", (), {"fields": {"postbirth_messaging": "TRUE"}})()
        with (
            mock.patch(
                "scripts.migrate_to_turn.process_fields.has_active_baby",
                return_value=False,
            ),
            mock.patch(
                "scripts.migrate_to_turn.process_fields.has_active_baby_between_1_and_2",
                return_value=False,
            ),
        ):
            self.assertEqual(get_user_type(contact), "alumni_user")

    def test_supporter_with_registered_status(self):
        """
        Supporters with registered status become supporter users
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"supporter": "TRUE", "supp_status": "registered"}},
        )()
        self.assertEqual(get_user_type(contact), "supporter")

    def test_supporter_without_registered_status(self):
        """
        Supporters without registered status become supporter leads
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"supporter": "TRUE", "supp_status": "pending"}},
        )()
        self.assertEqual(get_user_type(contact), "supporter_lead")

    def test_supporter_with_none_status(self):
        """
        Supporters with missing status values become supporter leads
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"supporter": "TRUE", "supp_status": None}},
        )()
        self.assertEqual(get_user_type(contact), "supporter_lead")

    def test_supporter_registered_status_is_normalized(self):
        """
        Supporter status should be stripped and case normalized
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"supporter": "TRUE", "supp_status": " Registered "}},
        )()
        self.assertEqual(get_user_type(contact), "supporter")

    def test_supporter_takes_priority_over_messaging_flags(self):
        """
        Supporter classification takes precedence over messaging-based types
        """
        contact = type(
            "Contact",
            (),
            {
                "fields": {
                    "supporter": "TRUE",
                    "supp_status": "registered",
                    "prebirth_messaging": "TRUE",
                    "public_messaging": "TRUE",
                }
            },
        )()
        self.assertEqual(get_user_type(contact), "supporter")

    def test_postbirth_without_active_baby_between_1_and_2_is_alumni_user_1_year(self):
        """
        Postbirth users with a baby between 1 and 2 years are alumni_user_1_year
        """
        contact = type("Contact", (), {"fields": {"postbirth_messaging": "TRUE"}})()
        with (
            mock.patch(
                "scripts.migrate_to_turn.process_fields.has_active_baby",
                return_value=False,
            ),
            mock.patch(
                "scripts.migrate_to_turn.process_fields.has_active_baby_between_1_and_2",
                return_value=True,
            ),
        ):
            self.assertEqual(get_user_type(contact), "alumni_user_1_year")

    def test_public_messaging_is_public_user(self):
        """
        Public messaging users are public users when no higher-priority flags exist
        """
        contact = type("Contact", (), {"fields": {"public_messaging": "TRUE"}})()
        self.assertEqual(get_user_type(contact), "public_user")

    def test_comprehensive_takes_priority_over_public_messaging(self):
        """
        Prebirth/postbirth messaging should win over public messaging
        """
        contact = type(
            "Contact",
            (),
            {"fields": {"prebirth_messaging": "TRUE", "public_messaging": "TRUE"}},
        )()
        self.assertEqual(get_user_type(contact), "comprehensive_user")


class HasActiveBabyTests(TestCase):
    def setUp(self):
        self.fixed_now = datetime(2026, 1, 1, tzinfo=pytz.utc)

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_true_for_baby_under_one(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2025-06-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertTrue(has_active_baby(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_true_for_baby_3_under_one(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob3": "2025-06-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertTrue(has_active_baby(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_baby_over_one(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2024-01-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_future_birth(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2026-02-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_invalid_date(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "not-a-date"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby(contact))


class HasActiveBabyBetween1And2Tests(TestCase):
    def setUp(self):
        self.fixed_now = datetime(2026, 1, 1, tzinfo=pytz.utc)

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_true_for_baby_older_than_one(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2024-06-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertTrue(has_active_baby_between_1_and_2(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_baby_under_one(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2025-06-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby_between_1_and_2(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_baby_older_than_two(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "2023-12-01"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby_between_1_and_2(contact))

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_false_for_invalid_date(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"baby_dob1": "not-a-date"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = self.fixed_now
        self.assertFalse(has_active_baby_between_1_and_2(contact))


class GetPregnancyInWeeksTests(TestCase):
    def test_returns_empty_string_when_edd_missing(self):
        contact = type("Contact", (), {"fields": {}})()
        self.assertEqual(get_pregnancy_in_weeks(contact), "")

    def test_returns_empty_string_when_edd_invalid(self):
        contact = type("Contact", (), {"fields": {"edd": "not-a-date"}})()
        self.assertEqual(get_pregnancy_in_weeks(contact), "")

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_calculates_weeks_with_same_year_expected_date(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"edd": "2026-10-30T00:00:00Z"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = datetime(2026, 2, 26, tzinfo=pytz.utc)
        self.assertEqual(get_pregnancy_in_weeks(contact), "4")

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_calculates_weeks_with_year_rollover_expected_date(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"edd": "2026-02-10T00:00:00Z"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = datetime(2026, 11, 15, tzinfo=pytz.utc)
        self.assertEqual(get_pregnancy_in_weeks(contact), "27")

    @mock.patch("scripts.migrate_to_turn.process_fields.datetime")
    def test_returns_empty_string_for_invalid_expected_date(self, datetime_mock):
        contact = type("Contact", (), {"fields": {"edd": "2024-02-29T00:00:00Z"}})()
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        datetime_mock.now.return_value = datetime(2026, 3, 1, tzinfo=pytz.utc)
        self.assertEqual(get_pregnancy_in_weeks(contact), "")


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


class GetYoungestDobTests(TestCase):
    def test_returns_none_when_no_valid_baby_dobs(self):
        contact = type("Contact", (), {"fields": {"baby_dob1": "not-a-date"}})()
        self.assertIsNone(get_youngest_dob(contact))

    def test_returns_latest_valid_baby_dob_in_processed_format(self):
        contact = type(
            "Contact",
            (),
            {
                "fields": {
                    "baby_dob1": "2024-01-02",
                    "baby_dob2": "2025-03-04",
                    "baby_dob3": "not-a-date",
                }
            },
        )()

        expected = datetime.fromisoformat("2025-03-04").astimezone(pytz.utc).isoformat()
        self.assertEqual(get_youngest_dob(contact), expected)
