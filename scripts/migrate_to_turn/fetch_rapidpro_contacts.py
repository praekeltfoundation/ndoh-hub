import csv
import os
from datetime import datetime

import pytz
from temba_client.v2 import TembaClient

from scripts.migrate_to_turn.process_fields import (
    get_next_anc_appointment_fields,
    get_next_pnc_appointment_fields,
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

env = "prd"  # qa or prd
RAPIDPRO_URL = f"https://rapidpro.{env}.momconnect.co.za"

START_DATE = "2023-01-01 00:00:00"
END_DATE = "2023-12-31 23:59:59"
LIMIT = 10000000
INCLUDE_OPTED_OUT = True
# We want to import beta testing users as opted out and give them the chance to opt in.
IMPORT_AS_OPTED_OUT = False
# This is to identify invited users and schedule the invite message.
MIGRATION_KEY = "test_batch_1"

MSISDN_FILTER = [
    msisdn.strip()
    for msisdn in os.environ.get("MSISDN_FILTER", "").split(",")
    if msisdn.strip()
]

FIELD_MAPPING = {
    "edd": {
        "turn_name": "pregnancy_expected_due_date",
        "process": process_datetime,
        "type": "custom",
    },
    "name": {"turn_name": "name", "type": "default"},
    "language": {"turn_name": "language", "type": "default"},
    "age": {
        "turn_name": "user_dob_year",
        "process": get_user_dob_year,
        "type": "custom",
    },
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
    "next_anc_appointment_": {"process": get_next_anc_appointment_fields},
    "next_pnc_appointment_": {"process": get_next_pnc_appointment_fields},
}


def get_readable_timestamp(dt=None):
    dt = dt or datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def log(message):
    print(f"[{get_readable_timestamp()}] {message}")


def get_field_data(contact):
    data = {}
    for rapidpro_field, turn_details in FIELD_MAPPING.items():
        turn_field = turn_details["turn_name"]

        if turn_details["type"] == "default":
            data[turn_field] = getattr(contact, rapidpro_field)
        else:
            data[turn_field] = contact.fields.get(rapidpro_field)

        if rapidpro_field == "language":
            language_value = data[turn_field]
            if language_value is None or str(language_value).strip() == "":
                data[turn_field] = "eng"

        if "process" in turn_details:
            data[turn_field] = turn_details["process"](data[turn_field])

    for new_field, details in NEW_TURN_FIELD_MAPPING.items():
        value = details["process"](contact)
        if isinstance(value, dict):
            data.update(value)
        else:
            data[new_field] = value

    return data


def get_wa_id(contact):
    for urn in contact.urns:
        if urn.startswith("whatsapp:"):
            return urn.split(":")[1]


def is_opted_out(contact):
    opted_out = str(contact.fields.get("opted_out", "FALSE") or "FALSE")
    return opted_out.upper() == "TRUE"


def get_contact_urn(msisdn):
    return msisdn if msisdn.startswith("whatsapp:") else f"whatsapp:{msisdn}"


def process_contact(
    contact, contacts, oldest_date, seen_wa_ids=None, apply_msisdn_filter=False
):
    wa_id = get_wa_id(contact)

    if is_opted_out(contact) and not INCLUDE_OPTED_OUT:
        return oldest_date, False

    if not wa_id:
        return oldest_date, False

    if apply_msisdn_filter and MSISDN_FILTER and wa_id not in MSISDN_FILTER:
        return oldest_date, False

    if seen_wa_ids is not None and wa_id in seen_wa_ids:
        return oldest_date, False

    data = get_field_data(contact)
    data["urn"] = wa_id
    contacts.append(data)

    if seen_wa_ids is not None:
        seen_wa_ids.add(wa_id)

    modified_on = contact.modified_on.astimezone(pytz.utc)
    if oldest_date is None or modified_on < oldest_date:
        oldest_date = modified_on

    return oldest_date, True


def get_rapidpro_contacts_by_msisdn(client):
    log(f"> Getting rapidpro contacts by MSISDN filter ({len(MSISDN_FILTER)} values)")
    contacts = []
    oldest_date = None
    seen_wa_ids = set()
    batch_number = 0

    for msisdn in MSISDN_FILTER:
        urn = get_contact_urn(msisdn)
        for contact_batch in client.get_contacts(urn=urn).iterfetches(
            retry_on_rate_exceed=True
        ):
            batch_number += 1
            log(f"Processing contact_batch #{batch_number} for {urn}")
            for contact in contact_batch:
                oldest_date, added = process_contact(
                    contact, contacts, oldest_date, seen_wa_ids=seen_wa_ids
                )

                if added and len(contacts) >= LIMIT:
                    return contacts, oldest_date

    return contacts, oldest_date


def get_rapidpro_contacts(client, start_date=None, end_date=None):
    log(f"> Getting rapidpro contacts from {start_date} to {end_date}")
    contacts = []
    oldest_date = end_date.replace(tzinfo=pytz.utc)
    for batch_number, contact_batch in enumerate(
        client.get_contacts(before=end_date, after=start_date).iterfetches(
            retry_on_rate_exceed=True
        ),
        start=1,
    ):
        log(f"Processing contact_batch #{batch_number}  -  {oldest_date}/{len(contacts)}")
        for contact in contact_batch:
            oldest_date, added = process_contact(
                contact, contacts, oldest_date, apply_msisdn_filter=True
            )

            if added and len(contacts) >= LIMIT:
                return contacts, oldest_date

    return contacts, oldest_date


def fetch_rapidpro_contacts(client):
    run_start = datetime.now().astimezone()
    log("Starting RapidPro contact fetch")

    if MSISDN_FILTER:
        contacts, oldest_date = get_rapidpro_contacts_by_msisdn(client)
        filename = f"contacts-{env}-msisdn-filter.csv"
    else:
        start_date = datetime.strptime(START_DATE, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(END_DATE, "%Y-%m-%d %H:%M:%S")
        contacts, oldest_date = get_rapidpro_contacts(client, start_date, end_date)
        start = START_DATE.split(" ")[0]
        end = END_DATE.split(" ")[0]
        filename = f"contacts-{env}-{start}-{end}.csv"

    log(f"Found: {len(contacts)}")
    log(f"Oldest modified on date: {oldest_date}")

    if contacts:
        log(f"File: {filename}")

        keys = contacts[0].keys()

        with open(filename, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(contacts)

    run_end = datetime.now().astimezone()
    log("Finished RapidPro contact fetch")
    log(f"Run started: {get_readable_timestamp(run_start)}")
    log(f"Run ended: {get_readable_timestamp(run_end)}")
    log(f"Total duration: {run_end - run_start}")


if __name__ == "__main__":
    client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])
    fetch_rapidpro_contacts(client)
