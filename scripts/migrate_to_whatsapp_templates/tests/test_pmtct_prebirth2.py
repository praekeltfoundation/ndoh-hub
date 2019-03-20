import unittest

from scripts.migrate_to_whatsapp_templates.pmtct_prebirth2 import (
    PMTCTPrebirth2Migration,
)


class TestPMTCTPrebirth2(unittest.TestCase):
    def setUp(self):
        self.pmtct_prebirth2 = PMTCTPrebirth2Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.pmtct_prebirth2.sequence_number_to_weeks(1), 31)
        self.assertEqual(self.pmtct_prebirth2.sequence_number_to_weeks(2), 31)
        self.assertEqual(self.pmtct_prebirth2.sequence_number_to_weeks(22), 41)

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
            self.pmtct_prebirth2.get_template_variables(message), ["32", "test"]
        )
