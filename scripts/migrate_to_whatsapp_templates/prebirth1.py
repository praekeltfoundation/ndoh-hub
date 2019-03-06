import csv
import json
import sys

from ndoh_hub.constants import WHATSAPP_LANGUAGE_MAP


def sequence_number_to_weeks(sequence_number):
    MSGS_PER_WEEK = 2
    STARTING_WEEK = 4
    return ((sequence_number + 1) // MSGS_PER_WEEK) + STARTING_WEEK


def run(input, output):
    reader = csv.DictReader(input)
    writer = csv.DictWriter(output, reader.fieldnames)
    writer.writeheader()
    for row in reader:
        metadata = json.loads(row["metadata"])
        metadata["template"] = {
            "name": "prebirth",
            "language": WHATSAPP_LANGUAGE_MAP[row["lang"]],
            "variables": [
                str(sequence_number_to_weeks(int(row["sequence_number"]))),
                row["text_content"],
            ],
        }
        row["metadata"] = json.dumps(metadata)
        writer.writerow(row)


if __name__ == "__main__":
    run(sys.stdin, sys.stdout)
