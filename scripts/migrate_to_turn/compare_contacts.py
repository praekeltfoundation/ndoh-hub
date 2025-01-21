import csv
import os
from urllib.parse import urljoin

import requests
from fetch_rapidpro_contacts import FIELD_MAPPING
from temba_client.v2 import TembaClient

RAPIDPRO_URL = "https://rapidpro.qa.momconnect.co.za"
TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"

WA_IDS = ["27836378531"]

rapidpro_client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])


def get_rapidpro_contact(wa_id):
    urn = f"whatsapp:{wa_id}"
    contact = rapidpro_client.get_contacts(urn=urn).first(retry_on_rate_exceed=True)
    data = {}

    for rapidpro_field, turn_details in FIELD_MAPPING.items():
        if turn_details["type"] == "default":
            data[rapidpro_field] = getattr(contact, rapidpro_field)
        else:
            data[rapidpro_field] = contact.fields[rapidpro_field]

    return data


def get_turn_contact(wa_id):
    headers = {
        "Authorization": "Bearer {}".format(os.environ["TURN_TOKEN"]),
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    response = requests.get(
        urljoin(TURN_URL, "/v1/contacts/{}/profile".format(wa_id)),
        headers=headers,
    )
    contact = response.json()["fields"]

    data = {}
    for rapidpro_field, turn_details in FIELD_MAPPING.items():
        data[rapidpro_field] = contact[turn_details["turn_name"]]
    return data


def compare_contacts():
    rows = []
    for wa_id in WA_IDS:
        rapidpro_data = get_rapidpro_contact(wa_id)
        turn_data = get_turn_contact(wa_id)

        row = {"wa_id": wa_id}
        for rapidpro_field in FIELD_MAPPING.keys():
            row[f"RP {rapidpro_field}"] = rapidpro_data[rapidpro_field]
            row[f"TURN {rapidpro_field}"] = turn_data[rapidpro_field]

        rows.append(row)

    with open("compare.csv", "w", encoding="utf-8") as f:
        fieldnames = rows[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    compare_contacts()
