import json
import time
from urllib.parse import urljoin

import psycopg2
import requests

DB = {
    "dbname": "ndoh_rapidpro_contacts",
    "user": "postgres",
    "port": 5432,
    "host": "localhost",
}

TURN_URL = "http://localhost:4000"
TURN_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJFbmdhZ2VkIiwiZXhwIjoxNjIyMTI0MjUxLCJpYXQiOjE1OTA1ODgyNjAsImlzcyI6IkVuZ2FnZWQiLCJqdGkiOiI4ZWNmMTYzNi1iMjI2LTQxMmEtYjNlYi1jZjI2ZGQ0M2VhYWQiLCJuYmYiOjE1OTA1ODgyNTksInN1YiI6Im51bWJlcjoyIiwidHlwIjoiYWNjZXNzIn0.9CuZHN84SIDiiSyChXWKDXeRU3Nl27s5HysWP38ck1QUihRXuaadViDVlIOXr6QRosTzEHqEo4hsGntsajjAjA"  # noqa


def get_turn_contact_details(wa_id):
    headers = {
        "Authorization": f"Bearer {TURN_TOKEN}",
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    response = requests.get(urljoin(TURN_URL, f"/v1/contacts/{wa_id}"), headers=headers)
    return json.loads(response.content)


def update_turn_contact_details(wa_id, details):
    headers = {
        "Authorization": f"Bearer {TURN_TOKEN}",
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    return requests.patch(
        urljoin(TURN_URL, f"/v1/contacts/{wa_id}"), json=details, headers=headers
    )


if __name__ == "__main__":
    conn = psycopg2.connect(**DB)

    cursor = conn.cursor("contact_urns")
    mapping_cursor = conn.cursor()

    mapping_cursor.execute(
        """
        SELECT key, uuid
        FROM contacts_contactfield
        WHERE org_id=5
        """
    )
    field_mapping = dict(mapping_cursor)

    print("Processing contacts...")  # noqa
    cursor.execute(
        """
        SELECT
            contacts_contacturn.path,
            contacts_contact.id,
            contacts_contact.fields
        FROM contacts_contacturn, contacts_contact
        WHERE contacts_contacturn.org_id = 5
            AND contacts_contacturn.contact_id  = contacts_contact.id
            AND contacts_contact.org_id = 5
            AND contacts_contacturn.scheme = 'whatsapp'
            AND fields is not null
            -- AND contacts_contact.id > 999
        ORDER BY contacts_contact.id
        """
    )

    total = 0
    updated = 0

    start, d_print = time.time(), time.time()
    for (path, contact_id, fields) in cursor:
        preferred_channel = fields.get(field_mapping["preferred_channel"], {}).get(
            "text", ""
        )

        if preferred_channel in ("WhatsApp", "SMS"):
            contact_details = get_turn_contact_details(path)

            is_fallback_active = contact_details.get("contact_details")

            update = True
            if preferred_channel == "WhatsApp" and is_fallback_active is not False:
                contact_details["is_fallback_active"] = False
            elif preferred_channel == "SMS" and is_fallback_active is not True:
                contact_details["is_fallback_active"] = True
            else:
                update = False

            if update:
                response = update_turn_contact_details(path, contact_details)

                if response.status_code != 200:
                    print(response.status_code)  # noqa
                    print(response.content)  # noqa
                    print(f"last contact_id: {contact_id}")  # noqa
                    raise Exception("update failed")

                updated += 1

        if time.time() - d_print > 1:
            print(  # noqa
                f"\rProcessed {total}/{updated} contacts at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()

        total += 1

    print(  # noqa
        f"\rProcessed {total}/{updated} contacts at {total/(time.time() - start):.0f}/s"
    )
