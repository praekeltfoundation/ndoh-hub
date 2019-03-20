from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.postbirth2 import Postbirth2Migration


class Postbirth2MigrationTests(TestCase):
    def setUp(self):
        self.postbirth2 = Postbirth2Migration()

    def test_get_template_variables(self):
        """
        Returns the number of months as the first variable, and the message content as
        the second variable
        """
        self.assertEqual(
            self.postbirth2.get_template_variables(
                {"sequence_number": "1", "text_content": "Test message"}
            ),
            ["3", "Test message"],
        )

    def test_get_months_from_sequence_number(self):
        """
        Returns correct number of months for the given sequence number
        """
        self.assertEqual(self.postbirth2.get_months_from_sequence_number(1), 3)
        self.assertEqual(self.postbirth2.get_months_from_sequence_number(37), 11)
        self.assertEqual(self.postbirth2.get_months_from_sequence_number(38), 12)
