import unittest

from scripts.migrate_to_whatsapp_templates.pmtct_postbirth1 import (
    PMTCTPostbirth1Migration,
)


class TestPMTCTPostbirth1(unittest.TestCase):
    def setUp(self):
        self.pmtct_postbirth1 = PMTCTPostbirth1Migration()

    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the postbirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(self.pmtct_postbirth1.sequence_number_to_weeks(1), 0)
        self.assertEqual(self.pmtct_postbirth1.sequence_number_to_weeks(2), 0)
        self.assertEqual(self.pmtct_postbirth1.sequence_number_to_weeks(4), 1)

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
            self.pmtct_postbirth1.get_template_variables(message), ["1", "test"]
        )
