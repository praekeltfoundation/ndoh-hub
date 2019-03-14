import unittest

from scripts.migrate_to_whatsapp_templates.prebirth6 import Prebirth6Migration


class Testprebirth6(unittest.TestCase):
    def setUp(self):
        self.prebirth6 = Prebirth6Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(1), 39)
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(2), 39)
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(3), 39)
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(7), 39)
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(14), 40)
        self.assertEqual(self.prebirth6.sequence_number_to_weeks(15), 41)

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
        self.assertEqual(self.prebirth6.get_template_variables(message), ["39", "test"])
