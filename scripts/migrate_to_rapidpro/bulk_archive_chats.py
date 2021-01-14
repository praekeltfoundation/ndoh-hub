import csv
import json
import time
from datetime import datetime

import pytz
import requests
from six.moves import urllib_parse
from temba_client.v2 import TembaClient

RAPIDPRO_URL = "https://rapidpro.qa.momconnect.co.za/"
RAPIDPRO_TOKEN = ""

TURN_URL = "https://whatsapp.turn.io"
TURN_TOKEN = ""

filename = "turn_open_chats.csv"
today = datetime.utcnow().replace(tzinfo=pytz.utc)

client = TembaClient(RAPIDPRO_URL, RAPIDPRO_TOKEN)


def get_whatsapp_messages(wa_id):
    headers = {
        "Authorization": "Bearer {}".format(TURN_TOKEN),
        "Content-Type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    response = requests.get(
        urllib_parse.urljoin(TURN_URL, "/v1/contacts/{}/messages".format(wa_id)),
        headers=headers,
    )
    return response.json()


def archive_turn_conversation(wa_id, message_id, reason):
    headers = {
        "Authorization": "Bearer {}".format(TURN_TOKEN),
        "Accept": "application/vnd.v1+json",
        "Content-Type": "application/json",
    }

    data = json.dumps({"before": message_id, "reason": reason})

    response = requests.post(
        urllib_parse.urljoin(TURN_URL, f"v1/chats/{wa_id}/archive"),
        headers=headers,
        data=data,
    )
    response.raise_for_status()
    return json.loads(response.content)


def can_archive_msg(inbound):
    labels = []
    for label in inbound["_vnd"]["v1"]["labels"]:
        labels.append(label["value"])

    archive = True
    if labels == []:
        archive = False
    else:
        for label in labels:
            if label not in ("TOO SHORT", "OK / THANKS"):
                archive = False

    if not archive:
        content = str(inbound.get("text", {}).get("body")).lower().strip()
        if content == "yes":
            archive = True

    return archive


total = 0
archived = 0
start, d_print = time.time(), time.time()

urns = []
for contact_batch in client.get_contacts(group="Waiting for helpdesk").iterfetches(
    retry_on_rate_exceed=True
):
    for contact in contact_batch:
        wa_id = None
        for urn in contact.urns:
            if "whatsapp" in urn:
                wa_id = urn.split(":")[1]

        if wa_id:
            urns.append(wa_id)

with open(filename, newline="") as csvfile:
    reader = csv.reader(csvfile, delimiter=",", quotechar='"')
    for row in reader:
        urn = row[0].replace("+", "")
        urns.append(urn)


urns = list(set(urns))
for urn in urns:
    rapidpro_urn = f"whatsapp:{urn}"
    msgs = get_whatsapp_messages(urn)
    state = msgs.get("chat", {}).get("state", "CLOSED")

    inbounds = []
    for msg in msgs.get("messages", []):
        delta = today - datetime.fromtimestamp(int(msg["timestamp"]), tz=pytz.utc)
        if delta.days > 30:
            break

        if msg["from"] == urn:
            inbounds.append(msg)

    archive = True
    for inbound in inbounds:
        if not can_archive_msg(inbound):
            archive = False
            break

    if archive:
        # Archive in turn and update Rapidpro
        if state == "OPEN" and inbounds:
            last_msg_id = inbounds[0]["id"]
            archive_turn_conversation(urn, last_msg_id, "Bulk archived")
        client.update_contact(
            rapidpro_urn,
            fields={
                "wait_for_helpdesk": "",
                "helpdesk_message_id": "",
                "helpdesk_timeout": "",
            },
        )
        archived += 1
    elif inbounds:
        # Don't archive but update fields in Rapidpro
        last_msg_id = inbounds[0]["id"]
        last_msg_timestamp = datetime.fromtimestamp(
            int(inbounds[0]["timestamp"])
        ).strftime("%Y-%m-%d")

        client.update_contact(
            rapidpro_urn,
            fields={
                "wait_for_helpdesk": "TRUE",
                "helpdesk_message_id": last_msg_id,
                "helpdesk_timeout": last_msg_timestamp,
            },
        )

    if time.time() - d_print > 1:
        print(  # noqa
            f"\rProcessed {archived}/{total} contacts at "
            f"{total/(time.time() - start):.0f}/s",
            end="",
        )
        d_print = time.time()

    total += 1

print(  # noqa
    f"\rProcessed {archived}/{total} contacts at "
    f"{total/(time.time() - start):.0f}/s"
)
