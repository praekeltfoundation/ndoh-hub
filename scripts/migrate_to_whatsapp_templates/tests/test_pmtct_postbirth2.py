from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.pmtct_postbirth2 import PMTCTPostbirth2Migration


class PMTCTPostbirth2MigrationTests(TestCase):
    def setUp(self):
        self.pmtct_postbirth2 = PMTCTPostbirth2Migration()

    def test_get_template_name(self):
        """
        If the sequence number is < 7, should be the first postbirth
        template, else should be the second postbirth template.
        """
        self.assertEqual(
            self.pmtct_postbirth2.get_template_name({"sequence_number": "6"}),
            "mc_postbirth1",
        )
        self.assertEqual(
            self.pmtct_postbirth2.get_template_name({"sequence_number": "7"}),
            "mc_postbirth2",
        )

    def test_get_template_variables_up_to_7_weeks(self):
        """
        Up to 7 weeks, the first variable should be the number of weeks, and the second
        should be the message content.
        """
        self.assertEqual(
            self.pmtct_postbirth2.get_template_variables(
                {"sequence_number": "5", "text_content": "Test message"}
            ),
            ["6", "Test message"],
        )

    def test_get_template_variables_over_7_weeks(self):
        """
        From 8 weeks onwards, the first variable should be the number of months, and
        the second should be the message content.
        """
        self.assertEqual(
            self.pmtct_postbirth2.get_template_variables(
                {"sequence_number": "7", "text_content": "Test message"}
            ),
            ["1", "Test message"],
        )

    def test_get_weeks_from_sequence_number(self):
        """
        Should return the correct number of weeks for the sequence number of the message
        """
        self.assertEqual(self.pmtct_postbirth2.get_weeks_from_sequence_number(1), 2)
        self.assertEqual(self.pmtct_postbirth2.get_weeks_from_sequence_number(2), 3)
        self.assertEqual(self.pmtct_postbirth2.get_weeks_from_sequence_number(6), 7)

    def test_get_months_from_sequence_number(self):
        """
        Returns correct number of months for the given sequence number
        """
        self.assertEqual(self.pmtct_postbirth2.get_months_from_sequence_number(1), 0)
        self.assertEqual(self.pmtct_postbirth2.get_months_from_sequence_number(7), 1)
        self.assertEqual(self.pmtct_postbirth2.get_months_from_sequence_number(50), 11)
