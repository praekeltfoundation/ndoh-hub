import unittest

from scripts.migrate_to_whatsapp_templates.prebirth4 import Prebirth4Migration


class Testprebirth4(unittest.TestCase):
    def setUp(self):
        self.prebirth4 = Prebirth4Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(1), 37)
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(2), 37)
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(3), 37)
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(4), 37)
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(14), 40)
        self.assertEqual(self.prebirth4.sequence_number_to_weeks(15), 40)

    def test_get_template_variables(self):
        message = {
            "id": "1",
            "messageset": "2",
            "sequence_number": "3",
            "lang": "zul_ZA",
            "text_content": "test",
            "binary_content": "",
            "metadata": "{}",
        }
        self.assertEqual(self.prebirth4.get_template_variables(message), ["37", "test"])
