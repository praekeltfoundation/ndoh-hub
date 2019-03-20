from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.loss import LossMigration


class LossMigrationTests(TestCase):
    def setUp(self):
        self.loss = LossMigration()

    def test_get_template_variables(self):
        """
        Returns the message content as the variable
        """
        self.assertEqual(
            self.loss.get_template_variables({"text_content": "Test message"}),
            ["Test message"],
        )
