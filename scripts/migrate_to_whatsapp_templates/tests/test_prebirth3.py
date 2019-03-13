import csv
import io
import json
import unittest

from scripts.migrate_to_whatsapp_templates.prebirth3 import Prebirth3Migration


class Testprebirth3(unittest.TestCase):
    def setUp(self):
        self.prebirth3 = Prebirth3Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.prebirth3.sequence_number_to_weeks(1), 36)
        self.assertEqual(self.prebirth3.sequence_number_to_weeks(2), 36)
        self.assertEqual(self.prebirth3.sequence_number_to_weeks(3), 36)
        self.assertEqual(self.prebirth3.sequence_number_to_weeks(14), 40)
        self.assertEqual(self.prebirth3.sequence_number_to_weeks(15), 40)

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
        self.assertEqual(self.prebirth3.get_template_variables(message), ["36", "test"])
