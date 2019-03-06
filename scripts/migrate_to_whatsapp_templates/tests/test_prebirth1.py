import csv
import io
import json
import unittest

from scripts.migrate_to_whatsapp_templates import prebirth1


class TestPrebirth1(unittest.TestCase):
    def test_sequence_number_to_weeks(self):
        """
        Given a certain sequence number for the prebirth 1 messageset, it should return
        the correct number of weeks pregnant
        """
        self.assertEqual(prebirth1.sequence_number_to_weeks(1), 5)
        self.assertEqual(prebirth1.sequence_number_to_weeks(2), 5)
        self.assertEqual(prebirth1.sequence_number_to_weeks(35), 22)
        self.assertEqual(prebirth1.sequence_number_to_weeks(36), 22)
        self.assertEqual(prebirth1.sequence_number_to_weeks(73), 41)
        self.assertEqual(prebirth1.sequence_number_to_weeks(74), 41)

    def test_prebirth_1(self):
        """
        With a valid CSV, it should output a valid CSV with all the same fields, except
        the metadata field should have a template key with the appropriate details.
        """
        input = io.StringIO()
        output = io.StringIO()
        writer = csv.writer(input)
        writer.writerow(
            [
                "id",
                "messageset",
                "sequence_number",
                "lang",
                "text_content",
                "binary_content",
                "metadata",
            ]
        )
        writer.writerow(["1", "2", "3", "zul_ZA", "Test message", "", '{"foo": "bar"}'])
        prebirth1.run(io.StringIO(input.getvalue()), output)

        reader = csv.DictReader(io.StringIO(output.getvalue()))
        [row] = list(reader)
        self.assertEqual(row["id"], "1")
        self.assertEqual(row["messageset"], "2")
        self.assertEqual(row["sequence_number"], "3")
        self.assertEqual(row["lang"], "zul_ZA")
        self.assertEqual(row["text_content"], "Test message")
        self.assertEqual(row["binary_content"], "")
        self.assertEqual(
            json.loads(row["metadata"]),
            {
                "foo": "bar",
                "template": {
                    "name": "prebirth",
                    "language": "uz",
                    "variables": ["6", "Test message"],
                },
            },
        )
