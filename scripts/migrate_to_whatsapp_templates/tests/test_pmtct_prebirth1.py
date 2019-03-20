import unittest

from scripts.migrate_to_whatsapp_templates.pmtct_prebirth1 import (
    PMTCTPrebirth1Migration,
)


class TestPMTCTPrebirth1(unittest.TestCase):
    def setUp(self):
        self.pmtct_prebirth1 = PMTCTPrebirth1Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.pmtct_prebirth1.sequence_number_to_weeks(1), 7)
        self.assertEqual(self.pmtct_prebirth1.sequence_number_to_weeks(2), 8)
        self.assertEqual(self.pmtct_prebirth1.sequence_number_to_weeks(36), 42)

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
            self.pmtct_prebirth1.get_template_variables(message), ["9", "test"]
        )
