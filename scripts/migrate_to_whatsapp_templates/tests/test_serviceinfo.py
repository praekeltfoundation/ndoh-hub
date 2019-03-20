from unittest import TestCase

from scripts.migrate_to_whatsapp_templates.serviceinfo import ServiceInfo


class ServiceInfoTests(TestCase):
    def setUp(self):
        self.serviceinfo = ServiceInfo()

    def test_get_template_variables(self):
        """
        Returns the message content as the variable
        """
        self.assertEqual(
            self.serviceinfo.get_template_variables({"text_content": "Test message"}),
            ["Test message"],
        )
