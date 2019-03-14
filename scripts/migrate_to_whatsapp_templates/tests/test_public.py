from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.public import PublicMigration


class PublicMigrationTests(TestCase):
    def setUp(self):
        self.public = PublicMigration()

    def test_get_template_variables(self):
        """
        Returns the message content as the variable
        """
        self.assertEqual(
            self.public.get_template_variables({"text_content": "Test message"}),
            ["Test message"],
        )
