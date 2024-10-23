import time

import psycopg2
from psycopg2.extras import Json

CORRECT_ORG_ID = 5
INCORRECT_ORG_ID = 1

DB = {
    "dbname": "ndoh_rapidpro_contacts",
    "user": "postgres",
    "port": 5432,
    "host": "localhost",
}


if __name__ == "__main__":
    conn = psycopg2.connect(**DB)
    update_conn = psycopg2.connect(**DB)

    cursor = conn.cursor("contact_urns")
    update_cursor = update_conn.cursor()

    update_cursor.execute(
        """
        SELECT key, uuid
        FROM contacts_contactfield
        WHERE org_id=%s
        """,
        (CORRECT_ORG_ID,),
    )
    field_mapping = dict(update_cursor)

    def clear_fields_for_optouts(contact_fields):
        for field in (
            "pmtct_messaging",
            "postbirth_messaging",
            "prebirth_messaging",
            "public_messaging",
            "baby_dob1",
            "baby_dob2",
            "baby_dob3",
            "edd",
        ):
            if field_mapping[field] in contact_fields:
                del contact_fields[field_mapping[field]]

        return contact_fields

    print("Processing contacts...")
    cursor.execute(
        """
        SELECT
            contacts_contacturn.id,
            contacts_contacturn.identity,
            contacts_contacturn.path,
            contacts_contacturn.scheme,
            contacts_contacturn.contact_id,
            contacts_contact.fields,
            contacts_contact.uuid
        FROM contacts_contacturn, contacts_contact
        WHERE contacts_contacturn.priority = 50
            AND contacts_contacturn.org_id = %s
            AND contacts_contacturn.contact_id  = contacts_contact.id
            AND contacts_contact.org_id = %s
        ORDER BY contacts_contacturn.contact_id DESC
        """,
        (INCORRECT_ORG_ID, CORRECT_ORG_ID),
    )

    total = 0
    total_total = 0
    empty_duplicate = 0
    no_duplicate_found = 0

    start, d_print = time.time(), time.time()
    for (
        original_urn_id,
        identity,
        path,
        scheme,
        contact_id,
        fields,
        contact_uuid,
    ) in cursor:
        total_total += 1

        # Unlink urn in incorrect org
        update_cursor.execute(
            """
            UPDATE contacts_contacturn
            SET contact_id = null, channel_id = null
            WHERE id = %s;
            """,
            (original_urn_id,),
        )

        update_cursor.execute(
            """
            SELECT
                contacts_contacturn.id,
                contacts_contact.fields,
                contacts_contact.uuid
            FROM contacts_contacturn, contacts_contact
            WHERE contacts_contacturn.org_id = %s
              AND identity = %s
              AND path = %s
              AND scheme = %s
              AND contacts_contacturn.contact_id = contacts_contact.id
              AND contacts_contact.id != %s
            """,
            (CORRECT_ORG_ID, identity, path, scheme, contact_id),
        )

        duplicate_contact = update_cursor.fetchone()

        if duplicate_contact:
            duplicate_urn_id = duplicate_contact[0]
            duplicate_fields = duplicate_contact[1] or {}
            duplicate_uuid = duplicate_contact[2]

            # link urn correct in correct org to original contact
            update_cursor.execute(
                "UPDATE contacts_contacturn SET contact_id = %s WHERE id = %s;",
                (contact_id, duplicate_urn_id),
            )

            # remove created on field, we don't want to overwrite that
            if field_mapping["created_on"] in duplicate_fields:
                del duplicate_fields[field_mapping["created_on"]]
            # this looks like it was supposed to be a flow field
            if field_mapping["webhook_failure_count"] in duplicate_fields:
                del duplicate_fields[field_mapping["webhook_failure_count"]]

            fields.update(duplicate_fields)

            if duplicate_fields == {}:
                # Skip if there is nothing to update
                empty_duplicate += 1
                update_conn.commit()
                continue
            elif (
                duplicate_fields.get(field_mapping["opted_out"], {}).get("text", "")
                == "TRUE"
                or duplicate_fields.get(field_mapping["loss_messaging"], {}).get(
                    "text", ""
                )
                == "TRUE"
            ):
                fields = clear_fields_for_optouts(fields)

            # update contact fields
            update_cursor.execute(
                """
                UPDATE contacts_contact
                SET fields = %s, modified_on = now()
                WHERE uuid = %s;
                """,
                (Json(fields), contact_uuid),
            )
            update_conn.commit()

            if time.time() - d_print > 1:
                print(
                    f"\rProcessed {total} ({empty_duplicate}/{no_duplicate_found})"
                    f" contacts at {total/(time.time() - start):.0f}/s",
                    end="",
                )
                d_print = time.time()

            total += 1
        else:
            no_duplicate_found += 1
            # This means correct urn is already linked
            update_conn.commit()

    print("")
    print(f"Processed: {total} ({empty_duplicate}/{no_duplicate_found})")
    print(f"Total records: {total_total}")
