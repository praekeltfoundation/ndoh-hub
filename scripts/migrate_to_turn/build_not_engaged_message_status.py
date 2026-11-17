"""Build Turn bulk-update CSVs for contacts that were not engaged."""

import csv
from pathlib import Path


DATA_DIR = Path(__file__).parent / "engage_data"


with (DATA_DIR / "not_engaged.csv").open(newline="") as source:
    not_engaged = {row["urn"].lstrip("+") for row in csv.DictReader(source)}

for group, status_field in (
    ("prebirth", "pregnancy_message_status"),
    ("postbirth", "baby_message_status"),
):
    with (DATA_DIR / f"{group}.csv").open(newline="") as source, (
        DATA_DIR / f"{group}_not_engaged.csv"
    ).open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["urn", status_field])
        for row in csv.DictReader(source):
            urn = row["whatsapp_phone_number"].lstrip("+")
            if urn in not_engaged:
                writer.writerow([urn, "false"])
