import csv
import io
import json
import unittest

from scripts.migrate_to_whatsapp_templates.prebirth2 import Prebirth2Migration


class TestPrebirth2(unittest.TestCase):
    def setUp(self):
        self.prebirth2 = Prebirth2Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.prebirth2.sequence_number_to_weeks(1), 31)
        self.assertEqual(self.prebirth2.sequence_number_to_weeks(2), 31)
        self.assertEqual(self.prebirth2.sequence_number_to_weeks(3), 31)
        self.assertEqual(self.prebirth2.sequence_number_to_weeks(30), 40)
        self.assertEqual(self.prebirth2.sequence_number_to_weeks(31), 41)

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
        self.assertEqual(self.prebirth2.get_template_variables(message), ["31", "test"])
