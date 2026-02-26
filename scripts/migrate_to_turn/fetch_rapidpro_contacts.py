import csv
import os
from datetime import datetime

import pytz
from temba_client.v2 import TembaClient

from scripts.migrate_to_turn.process_fields import (
    get_next_pnc_appointment_child_index,
    get_pregnancy_in_weeks,
    get_user_babies,
    get_user_dob_year,
    get_user_type,
    get_youngest_dob,
    process_baby_loss_status,
    process_datetime,
    process_opted_in,
    process_pregnancy_loss_status,
    process_truthy,
    to_lowercase,
)

RAPIDPRO_URL = "https://rapidpro.qa.momconnect.co.za"

START_DATE = "2026-02-24 01:13:06"
END_DATE = "2026-02-26 19:13:06"
LIMIT = 1000
INCLUDE_OPTED_OUT = False
# We want to import beta testing users as opted out and give them the chance to opt in.
IMPORT_AS_OPTED_OUT = True
# This is to identify invited users and schedule the invite message.
MIGRATION_KEY = "beta_testing_batch_1"

MSISDN_FILTER = (
    os.environ.get("MSISDN_FILTER", "").split(",")
    if os.environ.get("MSISDN_FILTER")
    else []
)

FIELD_MAPPING = {
    "edd": {
        "turn_name": "pregnancy_expected_due_date",
        "process": process_datetime,
        "type": "custom",
    },
    "name": {"turn_name": "name", "type": "default"},
    "language": {"turn_name": "language", "type": "default"},
    "age": {"turn_name": "user_dob_year", "process": get_user_dob_year, "type": "custom"},
    "research_consent": {
        "turn_name": "research_consent",
        "process": to_lowercase,
        "type": "custom",
    },
    "facility_code": {"turn_name": "clinic_code", "type": "custom"},
    "registered_by": {"turn_name": "referred_number", "type": "custom"},
    "education": {"turn_name": "education", "type": "custom"},
    "opted_out": {
        "turn_name": "opted_in",
        "process": lambda value: process_opted_in(value, IMPORT_AS_OPTED_OUT),
        "type": "custom",
    },
    "prebirth_messaging": {
        "turn_name": "pregnancy_message_status",
        "process": process_truthy,
        "type": "custom",
    },
    "postbirth_messaging": {
        "turn_name": "baby_message_status",
        "process": process_truthy,
        "type": "custom",
    },
    "underage_mother": {
        "turn_name": "minor_healthcare_consent",
        "type": "custom",
        "process": process_truthy,
    },
    "optout_reason": {"turn_name": "opt_out_reason", "type": "custom"},
    "preferred_channel": {
        "turn_name": "active_channel",
        "type": "custom",
        "process": to_lowercase,
    },
    "popi_consent": {
        "turn_name": "privacy_policy_accepted",
        "type": "custom",
        "process": process_truthy,
    },
    # province: we don't have the field but can derive it from clinic code later
    # area: we don't have the field but can derive it from clinic code later
}

NEW_TURN_FIELD_MAPPING = {
    "pregnancy_in_weeks": {"process": get_pregnancy_in_weeks},
    "user_type": {"process": get_user_type},
    "baby_loss_status": {"process": process_baby_loss_status},
    "pregnancy_loss_status": {"process": process_pregnancy_loss_status},
    "is_new_user": {"process": lambda contact: "no"},
    "babies": {"process": get_user_babies},
    "youngest_dob": {"process": get_youngest_dob},
    "migration_key": {"process": lambda contact: MIGRATION_KEY},
    "next_pnc_appointment_child_index": {"process": get_next_pnc_appointment_child_index},
}


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


def get_rapidpro_contacts(client, start_date=None, end_date=None):
    print(f"> Getting rapidpro contacts from {start_date} to {end_date}")
    contacts = []
    oldest_date = end_date.replace(tzinfo=pytz.utc)
    for contact_batch in client.get_contacts(
        before=end_date, after=start_date
    ).iterfetches(retry_on_rate_exceed=True):
        for contact in contact_batch:
            wa_id = get_wa_id(contact)

            if is_opted_out(contact) and not INCLUDE_OPTED_OUT:
                continue

            # TODO: filtering for testing only, remove later()
            if wa_id and MSISDN_FILTER and wa_id not in MSISDN_FILTER:
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


def fetch_rapidpro_contacts(client):
    start_date = datetime.strptime(START_DATE, "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d %H:%M:%S")

    contacts, oldest_date = get_rapidpro_contacts(client, start_date, end_date)

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


if __name__ == "__main__":
    client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])
    fetch_rapidpro_contacts(client)
