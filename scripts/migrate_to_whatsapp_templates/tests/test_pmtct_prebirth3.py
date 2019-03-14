import unittest

from scripts.migrate_to_whatsapp_templates.pmtct_prebirth3 import (
    PMTCTPrebirth3Migration,
)


class TestPMTCTPrebirth3(unittest.TestCase):
    def setUp(self):
        self.pmtct_prebirth3 = PMTCTPrebirth3Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.pmtct_prebirth3.sequence_number_to_weeks(1), 36)
        self.assertEqual(self.pmtct_prebirth3.sequence_number_to_weeks(3), 36)
        self.assertEqual(self.pmtct_prebirth3.sequence_number_to_weeks(19), 42)

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
        self.assertEqual(
            self.pmtct_prebirth3.get_template_variables(message), ["36", "test"]
        )
