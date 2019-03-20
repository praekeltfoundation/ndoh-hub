from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.postbirth1 import Postbirth1Migration


class Postbirth1MigrationTests(TestCase):
    def setUp(self):
        self.postbirth1 = Postbirth1Migration()

    def test_get_template_name(self):
        """
        If the sequence number is < 17, should be the first postbirth template, else
        should be the second postbirth template.
        """
        self.assertEqual(
            self.postbirth1.get_template_name({"sequence_number": "16"}),
            "mc_postbirth1",
        )
        self.assertEqual(
            self.postbirth1.get_template_name({"sequence_number": "17"}),
            "mc_postbirth2",
        )

    def test_get_template_variables_up_to_7_weeks(self):
        """
        Up to 7 weeks, the first variable should be the number of weeks, and the second
        should be the message content.
        """
        self.assertEqual(
            self.postbirth1.get_template_variables(
                {"sequence_number": "16", "text_content": "Test message"}
            ),
            ["7", "Test message"],
        )

    def test_get_template_variables_over_7_weeks(self):
        """
        From 8 weeks onwards, the first variable should be the number of months, and
        the second should be the message content.
        """
        self.assertEqual(
            self.postbirth1.get_template_variables(
                {"sequence_number": "17", "text_content": "Test message"}
            ),
            ["1", "Test message"],
        )

    def test_get_weeks_from_sequence_number(self):
        """
        Should return the correct number of weeks for the sequence number of the message
        """
        self.assertEqual(self.postbirth1.get_weeks_from_sequence_number(1), 0)
        self.assertEqual(self.postbirth1.get_weeks_from_sequence_number(2), 0)
        self.assertEqual(self.postbirth1.get_weeks_from_sequence_number(3), 1)
        self.assertEqual(self.postbirth1.get_weeks_from_sequence_number(16), 7)

    def test_get_months_from_sequence_number(self):
        """
        Returns correct number of months for the given sequence number
        """
        self.assertEqual(self.postbirth1.get_months_from_sequence_number(1), 0)
        self.assertEqual(self.postbirth1.get_months_from_sequence_number(18), 1)
        self.assertEqual(self.postbirth1.get_months_from_sequence_number(19), 2)
        self.assertEqual(self.postbirth1.get_months_from_sequence_number(30), 3)
