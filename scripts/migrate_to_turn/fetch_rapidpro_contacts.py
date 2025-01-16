import csv
import os
from datetime import datetime

import pytz
from process_fields import process_datetime
from temba_client.v2 import TembaClient

RAPIDPRO_URL = "https://rapidpro.qa.momconnect.co.za"

START_DATE = "2024-01-01 14:13:06"
END_DATE = "2025-01-07 19:13:06"
LIMIT = 1000

# TODO: add all the fields here: <rapidpro-field-name>: <details>
FIELD_MAPPING = {
    "edd": {"turn_name": "test", "process": process_datetime, "type": "custom"},
    "name": {"turn_name": "name", "type": "default"},
}

client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])


def get_field_data(contact):
    data = {}
    for rapidpro_field, turn_details in FIELD_MAPPING.items():
        turn_field = turn_details["turn_name"]

        if turn_details["type"] == "default":
            data[turn_field] = getattr(contact, rapidpro_field)
        else:
            data[turn_field] = contact.fields[rapidpro_field]

        if "process" in turn_details:
            data[turn_field] = turn_details["process"](data[turn_field])

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
    latest_date = start_date.replace(tzinfo=pytz.utc)
    for contact_batch in client.get_contacts(
        before=end_date, after=start_date, reverse=True
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
                if modified_on > latest_date:
                    latest_date = modified_on

                if len(contacts) >= LIMIT:
                    return contacts, latest_date

    return contacts, latest_date


if __name__ == "__main__":
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d %H:%M:%S")

    contacts, latest_date = get_rapidpro_contacts(start_date, end_date)

    print(f"Found: {len(contacts)}")
    print(f"Latest modified on date: {latest_date}")

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
