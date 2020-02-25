from collections import defaultdict
import psycopg2
from uuid import uuid4
import json
from typing import Tuple

PREBIRTH: Tuple[Tuple[str, str, Tuple[int, ...], int], ...] = (
    ("pmtct_prebirth.patient.1", "PMTCT 1 SMS", (0,), 5),
    ("pmtct_prebirth.patient.2", "PMTCT 2 SMS", (0, 3), 30),
    ("pmtct_prebirth.patient.3", "PMTCT 3 SMS", (0, 2, 4), 35),
    ("momconnect_prebirth.hw_full.1", "Prebirth 1 SMS", (0, 3), 5),
    ("momconnect_prebirth.hw_full.2", "Prebirth 2 SMS", (0, 2, 4), 31),
    ("momconnect_prebirth.hw_full.3", "Prebirth 3 SMS", (0, 2, 4), 36),
    ("momconnect_prebirth.hw_full.4", "Prebirth 4 SMS", (0, 1, 2, 4), 37),
    ("momconnect_prebirth.hw_full.5", "Prebirth 5 SMS", (0, 1, 2, 3, 4), 38),
    ("momconnect_prebirth.hw_full.6", "Prebirth 6 SMS", (0, 1, 2, 3, 4, 5, 6), 39),
)

POSTBIRTH: Tuple[Tuple[str, str, Tuple[int, ...], int], ...] = (
    ("momconnect_postbirth.hw_full.1", "Postbirth SMS", (0, 3), 0),
    ("momconnect_postbirth.hw_full.2", "Postbirth SMS", (0,), 15),
    ("pmtct_postbirth.patient.1", "PMTCT Postbirth SMS", (0, 3), 0),
    ("pmtct_postbirth.patient.2", "PMTCT Postbirth SMS", (0,), 2),
)

LOSS: Tuple[Tuple[str, str, Tuple[int, ...]], ...] = (
    ("loss_babyloss.patient.1", "Babyloss SMS", (0, 3)),
    ("loss_stillbirth.patient.1", "Stillbirth SMS", (0,)),
    ("loss_miscarriage.patient.1", "Miscarriage SMS", (0, 3)),
)

PUBLIC: Tuple[Tuple[str, str, Tuple[int, ...]], ...] = (
    ("momconnect_prebirth.patient.1", "Public SMS", (0, 3)),
)

POPI: Tuple[str, str] = ("popi.hw_full.1", "POPI SMS")


def create_campaign(name: str, group: str) -> dict:
    return {
        "uuid": str(uuid4()),
        "name": name,
        "group": {"uuid": str(uuid4()), "name": group},
        "events": [],
    }


def create_event(offset: int, message: dict, label: dict) -> dict:
    return {
        "uuid": str(uuid4()),
        "offset": offset,
        "unit": "D",
        "event_type": "M",
        "delivery_hour": 8,
        "message": message,
        "relative_to": label,
        "start_mode": "I",
        "base_language": "eng",
    }


def write_campaign(short_name: str, campaign: dict) -> None:
    with open(f"{short_name}.json", "w") as f:
        f.write(
            json.dumps(
                {
                    "version": "13",
                    "site": "https://rapidpro.qa.momconnect.co.za",
                    "flows": [],
                    "campaigns": [campaign],
                }
            )
        )


def get_messages(short_name):
    cursor.execute(
        """
    SELECT sequence_number, text_content, lang
    FROM contentstore_message as message
    JOIN contentstore_messageset as messageset
    ON messageset.id = message.messageset_id
    WHERE messageset.short_name = %s
    """,
        (short_name,),
    )
    msgs: defaultdict = defaultdict(dict)
    for (sequence, content, language) in cursor:
        msgs[sequence][language.rstrip("_ZA")] = content
    return msgs


if __name__ == "__main__":
    password = input("Stage based messenger password? ")
    conn = psycopg2.connect(
        dbname="stage_based_messaging",
        user="stage_based_messaging",
        password=password,
        host="localhost",
        port=7000,
    )
    cursor = conn.cursor()

    for short_name, group, offsets, start_week in PREBIRTH:
        campaign = create_campaign(group, group)
        msgs = get_messages(short_name)

        # Loop through weeks
        for seq in range(0, len(msgs), len(offsets)):
            week = seq // len(offsets)
            # Loop through messages in week
            for offset_i, offset in enumerate(offsets):
                msg = msgs[seq + 1 + offset_i]
                if not msg:
                    continue
                campaign["events"].append(
                    create_event(
                        (-40 + start_week + week) * 7 + offset,
                        msg,
                        {"label": "Estimated Due Date", "key": "edd"},
                    )
                )

        write_campaign(short_name, campaign)

    for short_name, group, offsets, start_week in POSTBIRTH:
        campaign = create_campaign(f"{group}{short_name[-1]}", group)
        msgs = get_messages(short_name)

        # Loop through weeks
        for seq in range(0, len(msgs), len(offsets)):
            week = seq // len(offsets)
            # Loop through messages in week
            for offset_i, offset in enumerate(offsets):
                msg = msgs[seq + 1 + offset_i]
                if not msg:
                    continue
                # Loop for each baby dob variable
                for i in range(1, 4):
                    campaign["events"].append(
                        create_event(
                            (start_week + week) * 7 + offset,
                            msg,
                            {"label": f"Baby Date of Birth {i}", "key": f"baby_dob{i}"},
                        )
                    )

        write_campaign(short_name, campaign)

    for short_name, group, offsets in LOSS:
        campaign = create_campaign(group, group)
        msgs = get_messages(short_name)

        # Loop through weeks
        for seq in range(0, len(msgs), len(offsets)):
            week = seq // len(offsets)
            # Loop through messages in week
            for offset_i, offset in enumerate(offsets):
                msg = msgs[seq + 1 + offset_i]
                if not msg:
                    continue
                campaign["events"].append(
                    create_event(
                        # Start at 1 day after registration
                        (week * 7 + offset) or 1,
                        msg,
                        {"label": "Optout Timestamp", "key": "optout_timestamp"},
                    )
                )

        write_campaign(short_name, campaign)

    for short_name, group, offsets in PUBLIC:
        campaign = create_campaign(group, group)
        msgs = get_messages(short_name)

        # Loop through weeks
        for seq in range(0, len(msgs), len(offsets)):
            week = seq // len(offsets)
            # Loop through messages in week
            for offset_i, offset in enumerate(offsets):
                msg = msgs[seq + 1 + offset_i]
                if not msg:
                    continue
                campaign["events"].append(
                    create_event(
                        # Start at 1 day after registration
                        (week * 7 + offset) or 1,
                        msg,
                        {
                            "label": "Public Registration Date",
                            "key": "public_registration_date",
                        },
                    )
                )

        write_campaign(short_name, campaign)

    short_name, group = POPI
    campaign = create_campaign(group, group)
    msgs = get_messages(short_name)
    campaign["events"].append(
        create_event(
            # Start at 1 day after registration
            1,
            msgs[1],
            {"label": "Registration Date", "key": "registration_date"},
        )
    )
    write_campaign(short_name, campaign)
