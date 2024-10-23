import time

import psycopg2

CORRECT_ORG_ID = 5
INCORRECT_ORG_ID = 1

DB = {"dbname": "rapidpro", "user": "postgres", "port": 5444, "host": "127.0.0.1"}

if __name__ == "__main__":
    conn = psycopg2.connect(**DB)
    update_conn = psycopg2.connect(**DB)

    cursor = conn.cursor("contact_urns")
    update_cursor = update_conn.cursor()

    print("Processing contact urns...")
    cursor.execute(
        """
        SELECT contacts_contacturn.id
        FROM contacts_contact, contacts_contacturn
        WHERE contacts_contact.id = contacts_contacturn.contact_id
        AND contacts_contact.org_id = %s
        AND contacts_contacturn.org_id = %s
        """,
        (CORRECT_ORG_ID, INCORRECT_ORG_ID),
    )

    total = 0
    error = 0

    start, d_print = time.time(), time.time()
    for (id,) in cursor:
        try:
            update_cursor.execute(
                "UPDATE contacts_contacturn SET org_id = %s WHERE id = %s;",
                (CORRECT_ORG_ID, id),
            )
            update_conn.commit()

            if time.time() - d_print > 1:
                print(
                    f"\rProcessed {total} identities at "
                    f"{total/(time.time() - start):.0f}/s",
                    end="",
                )
                d_print = time.time()

            total += 1
        except psycopg2.IntegrityError:
            error += 1
            update_conn.rollback()

    print(f"\nProcessed {total} contacts in {time.time() - start:.0f}s")

    start = time.time()
    update_conn.commit()

    print(f"Committed changes in {time.time() - start:.0f}s")
    print(f"Failed with IntegrityError: {error}")
