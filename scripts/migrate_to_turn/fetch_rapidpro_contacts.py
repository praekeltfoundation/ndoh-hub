import csv
import os
from datetime import datetime

import pytz
from process_fields import (
    get_user_babies,
    get_user_tier,
    get_user_type,
    process_datetime,
    to_lowercase,
)
from temba_client.v2 import TembaClient

RAPIDPRO_URL = "https://rapidpro.qa.momconnect.co.za"

START_DATE = "2025-11-01 01:13:06"
END_DATE = "2026-01-12 19:13:06"
LIMIT = 1000

# TODO: add all the fields here: <rapidpro-field-name>: <details>
FIELD_MAPPING = {
    "edd": {
        "turn_name": "pregnancy_expected_due_date",
        "process": process_datetime,
        "type": "custom",
    },
    "name": {"turn_name": "name", "type": "default"},
    "language": {"turn_name": "language", "type": "default"},
    "research_consent": {"turn_name": "research_consent", "process": to_lowercase, "type": "custom"},
    "clinic_code": {"turn_name": "clinic_code", "type": "custom"},
}

NEW_TURN_FIELD_MAPPING = {
    "user_tier": {"process": get_user_tier},
    "user_type": {"process": get_user_type},
    "babies": {"process": get_user_babies},
}

client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])


def get_field_data(contact):
    data = {}
    for rapidpro_field, turn_details in FIELD_MAPPING.items():
        turn_field = turn_details["turn_name"]

        if turn_details["type"] == "default":
            data[turn_field] = getattr(contact, rapidpro_field)
        else:
            data[turn_field] = contact.fields.get(rapidpro_field)

        if "process" in turn_details:
            data[turn_field] = turn_details["process"](data[turn_field])

    for new_field, details in NEW_TURN_FIELD_MAPPING.items():
        data[new_field] = details["process"](contact)

    return data


def get_wa_id(contact):
    for urn in contact.urns:
        if urn.startswith("whatsapp:"):
            return urn.split(":")[1]


def is_opted_out(contact):
    opted_out = str(contact.fields.get("opted_out", "FALSE") or "FALSE")
    return opted_out.upper() == "TRUE"


def get_rapidpro_contacts(start_date=None, end_date=None):
    print(f"> Getting rapidpro contacts from {start_date} to {end_date}")
    contacts = []
    oldest_date = end_date.replace(tzinfo=pytz.utc)
    for contact_batch in client.get_contacts(
        before=end_date, after=start_date
    ).iterfetches(retry_on_rate_exceed=True):
        for contact in contact_batch:
            wa_id = get_wa_id(contact)

            if is_opted_out(contact):
                continue

            if wa_id:
                data = get_field_data(contact)
                data["urn"] = wa_id
                contacts.append(data)

                modified_on = contact.modified_on.astimezone(pytz.utc)
                if modified_on < oldest_date:
                    oldest_date = modified_on

                if len(contacts) >= LIMIT:
                    return contacts, oldest_date

    return contacts, oldest_date


if __name__ == "__main__":
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d %H:%M:%S")

    contacts, oldest_date = get_rapidpro_contacts(start_date, end_date)

    print(f"Found: {len(contacts)}")
    print(f"Oldest modified on date: {oldest_date}")

    if contacts:
        start = START_DATE.split(" ")[0]
        end = END_DATE.split(" ")[0]
        filename = f"contacts-{start}-{end}.csv"

        print(f"File: {filename}")

        keys = contacts[0].keys()

        with open(filename, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(contacts)
