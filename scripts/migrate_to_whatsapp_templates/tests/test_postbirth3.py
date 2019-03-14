from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.postbirth3 import Postbirth3Migration


class Postbirth3MigrationTests(TestCase):
    def setUp(self):
        self.postbirth3 = Postbirth3Migration()

    def test_get_template_variables(self):
        """
        Returns the number of months as the first variable, and the message content as
        the second variable
        """
        self.assertEqual(
            self.postbirth3.get_template_variables({"text_content": "Test message"}),
            ["Test message"],
        )
