import datetime
import time

import iso8601
import psycopg2
from temba_client.v2 import TembaClient

RAPIDPRO_URL = "https://rapidpro.prd.momconnect.co.za/"
RAPIDPRO_TOKEN = ""

DB = {
    "dbname": "ndoh_rapidpro",
    "user": "ndoh_rapidpro",
    "port": 7000,
    "host": "localhost",
    "password": "",
}


if __name__ == "__main__":
    rapidpro_client = TembaClient(RAPIDPRO_URL, RAPIDPRO_TOKEN)
    conn = psycopg2.connect(**DB)

    cursor = conn.cursor("contacts")
    mapping_cursor = conn.cursor()

    mapping_cursor.execute(
        """
        SELECT key, uuid
        FROM contacts_contactfield
        WHERE org_id=5
        """
    )
    field_mapping = dict(mapping_cursor)

    now = datetime.date.today()

    print("Processing contacts...")  # noqa
    cursor.execute(
        """
        SELECT
            distinct contacts_contact.id,
            contacts_contact.uuid,
            contacts_contact.fields,
            contacts_contactgroup.id,
            contacts_contact.created_on
        FROM contacts_contactgroup,
            campaigns_campaign,
            contacts_contactgroup_contacts
                left outer join campaigns_eventfire
                on campaigns_eventfire.contact_id =
                    contacts_contactgroup_contacts.contact_id,
            contacts_contact
        WHERE contacts_contactgroup.org_id = 5
            and contacts_contactgroup.id in (324, 325)
        AND campaigns_campaign.group_id = contacts_contactgroup.id
        and contacts_contactgroup_contacts.contactgroup_id = contacts_contactgroup.id
        and campaigns_eventfire.contact_id is null
        and contacts_contactgroup_contacts.contact_id = contacts_contact.id
        """
    )

    total = 0
    updated = 0
    contact_id = 0

    start, d_print = time.time(), time.time()
    for contact_id, contact_uuid, fields, _group_id, _created_on in cursor:
        should_receive_msgs = False
        fields_to_update = {}

        for date_field in ("baby_dob1", "baby_dob2", "baby_dob3"):
            date_value = fields.get(field_mapping[date_field], {}).get("datetime")
            text_value = fields.get(field_mapping[date_field], {}).get("text")

            if date_value:
                date_obj = iso8601.parse_date(date_value)

                delta = datetime.date.today() - date_obj.date()
                if delta.days <= 730:
                    should_receive_msgs = True
                    fields_to_update[date_field] = text_value

        if should_receive_msgs:
            updated += 1
            rapidpro_client.update_contact(contact_uuid, fields=fields_to_update)

        if time.time() - d_print > 1:
            print(  # noqa
                f"\rProcessed {updated}/{total} contacts at "
                f"{total/(time.time() - start):.0f}/s - ({contact_id})",
                end="",
            )
            d_print = time.time()

        total += 1

    print(  # noqa
        f"\rProcessed {updated}/{total} contacts at "
        f"{total/(time.time() - start):.0f}/s - ({contact_id})"
    )
