import json
import time
from datetime import datetime

import psycopg2
from django.utils.dateparse import parse_date, parse_datetime
from psycopg2.extras import Json, execute_values
from pytz import utc

ORG = 1
USER = 2


def fields_from_contact(field_mapping, contact):
    """
    Returns the fields to insert into RapidPro given the mapping and contact
    """
    ret = {}

    def boolean_field(field, value):
        if contact.get(field) is True:
            ret[field_mapping[field]] = {"text": "TRUE"}
        elif contact.get(field) is False:
            ret[field_mapping[field]] = {"text": "FALSE"}

    def normalize_timestamp(value):
        try:
            return parse_datetime(value).isoformat()
        except Exception:
            pass
        try:
            value = parse_date(value)
            value = datetime.combine(value, datetime.min.time())
            return value.replace(tzinfo=utc).isoformat()
        except Exception:
            pass

    def datetime_field(field, value):
        value = normalize_timestamp(value)
        if value:
            ret[field_mapping[field]] = {"text": value, "datetime": value}

    def string_field(field, value):
        if value:
            ret[field_mapping[field]] = {"text": value}

    boolean_field("consent", contact.get("consent"))
    baby_dobs = map(normalize_timestamp, contact.get("baby_dobs", []))
    baby_dobs = sorted(set(baby_dobs), reverse=True)
    for i, baby_dob in enumerate(baby_dobs[:3], 1):
        datetime_field(f"baby_dob_{i}", baby_dob)
    datetime_field("date_of_birth", contact.get("mom_dob"))
    datetime_field("edd", contact.get("edd"))
    string_field("facility_code", contact.get("faccode"))
    string_field(
        "identification_type",
        {"sa_id": "sa_id", "passport": "passport", "none": "dob"}.get(
            contact.get("id_type")
        ),
    )
    string_field("id_number", contact.get("sa_id_no"))
    string_field("optout_reason", contact.get("optout_reason"))
    datetime_field("optout_timestamp", contact.get("optout_timestamp"))
    string_field("passport_number", contact.get("passport_no"))
    string_field("passport_origin", contact.get("passport_origin"))
    string_field("pmtct_risk", contact.get("pmtct_risk"))
    string_field("preferred_channel", contact.get("channel"))
    datetime_field("public_registration_date", contact.get("public_registration_date"))
    string_field("registered_by", contact.get("msisdn_device"))

    return ret


if __name__ == "__main__":
    conn = psycopg2.connect(dbname="temba", user="temba", password="temba")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT key, uuid
        FROM contacts_contactfield
        WHERE org_id=%s
        """,
        (ORG,),
    )
    field_mapping = dict(cursor)

    cursor.execute(
        """
        SELECT name, id
        FROM contacts_contactgroup
        WHERE org_id=%s
        """,
        (ORG,),
    )
    group_mapping = dict(cursor)

    cursor.execute(
        """
        SELECT ltrim(path, '+'), contact_id
        FROM contacts_contacturn
        WHERE org_id=%s
        """,
        (ORG,),
    )
    msisdn_mapping = dict(cursor)

    total = 0
    start, d_print = time.time(), time.time()
    for l in open("results.json"):
        contact = json.loads(l)
        msisdn = contact["msisdn"]
        name = (
            f"{contact.get('mom_given_name', '')} {contact.get('mom_family_name', '')}"
        ).strip()

        contact_id = msisdn_mapping.get(msisdn.lstrip("+"))

        if contact_id:
            cursor.execute(
                """
                UPDATE contacts_contact
                SET
                    uuid=%s, name=%s, language=%s,
                    fields=COALESCE(fields,'{}'::jsonb) || %s, modified_on=%s
                WHERE id = %s
                """,
                (
                    contact["uuid"],
                    name or None,
                    contact.get("language"),
                    Json(fields_from_contact(field_mapping, contact)),
                    datetime.now(tz=utc),
                    contact_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO contacts_contact (
                    is_active, created_on, modified_on, uuid, org_id, name, language,
                    is_blocked, is_stopped, fields, modified_by_id, created_by_id
                )
                VALUES ( true, %s, %s, %s, %s, %s, %s, false, false, %s, %s, %s )
                RETURNING
                id
                """,
                (
                    datetime.now(tz=utc),
                    datetime.now(tz=utc),
                    contact["uuid"],
                    ORG,
                    name or None,
                    contact.get("language"),
                    Json(fields_from_contact(field_mapping, contact)),
                    USER,
                    USER,
                ),
            )
            [contact_id] = cursor.fetchone()

        wa = msisdn.lstrip("+")
        execute_values(
            cursor,
            """
            INSERT INTO contacts_contacturn (
                contact_id, identity, path, display, scheme, org_id, priority,
                channel_id, auth
            )
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            ((contact_id, f"whatsapp:{wa}", wa, None, "whatsapp", 1, 50, None, None),),
        )

        execute_values(
            cursor,
            """
            INSERT INTO contacts_contactgroup_contacts ( contactgroup_id, contact_id )
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            (
                (group_mapping[group], contact_id)
                for group in set(contact.get("subscriptions", []))
            ),
        )

        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} identities at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1

    print(f"\nProcessed {total} identities in {time.time() - start:.0f}s")

    start = time.time()
    conn.commit()
    print(f"Committed changes in {time.time() - start:.0f}s")
