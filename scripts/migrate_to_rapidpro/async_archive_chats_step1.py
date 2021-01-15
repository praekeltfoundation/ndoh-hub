import asyncio
import csv
import os
import sys
import time
from datetime import datetime

import aiohttp
import pytz
from six.moves import urllib_parse

CONCURRENCY = 20
TURN_URL = "https://whatsapp.praekelt.org"
OUTPUT_FILE = "contacts_to_update.csv"

processed = 0
eligible_archive = 0
eligible_update = 0
start, d_print = time.time(), time.time()
today = datetime.utcnow().replace(tzinfo=pytz.utc)


async def get_whatsapp_messages(session, wa_id):
    url = urllib_parse.urljoin(TURN_URL, f"/v1/contacts/{wa_id}/messages")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    async with session.get(url, headers=headers) as response:
        response_body = await response.json()
        return response_body


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


async def process_conversation(session, row, writer):
    global processed
    global eligible_archive
    global eligible_update
    global d_print
    global start

    processed += 1

    whatsapp_id = str(row["owner"]).replace("+", "")

    result = await get_whatsapp_messages(session, whatsapp_id)
    state = result.get("chat", {}).get("state", "CLOSED")

    inbounds = []
    for msg in result.get("messages", []):
        delta = today - datetime.fromtimestamp(int(msg["timestamp"]), tz=pytz.utc)
        if delta.days > 30:
            break

        if msg["from"] == whatsapp_id:
            inbounds.append(msg)

    archive = True
    for inbound in inbounds:
        if not can_archive_msg(inbound):
            archive = False
            break

    rp_row = {
        "action": "UPDATE",
        "owner": row["owner"],
        "wait_for_helpdesk": "",
        "last_message_id": "",
        "helpdesk_timeout": "",
    }
    if archive:
        if state == "OPEN" and inbounds:
            row["action"] = "ARCHIVE"
            row["last_message_id"] = inbounds[0]["id"]
            writer.writerow(row)
            eligible_archive += 1

        writer.writerow(rp_row)
        eligible_update += 1

    elif inbounds:
        # Don't archive but update fields in Rapidpro
        rp_row["wait_for_helpdesk"] = "TRUE"
        rp_row["last_message_id"] = inbounds[0]["id"]
        rp_row["helpdesk_timeout"] = datetime.fromtimestamp(
            int(inbounds[0]["timestamp"])
        ).strftime("%Y-%m-%d")

        writer.writerow(rp_row)
        eligible_update += 1

    if time.time() - d_print > 1:
        print(  # noqa
            f"\rProcessed {processed} ({eligible_archive} & {eligible_update}"
            f" contacts at {processed/(time.time() - start):.0f}/s",
            end="",
        )
        d_print = time.time()


async def bounded_process_conversation(session, row, writer, sem):
    async with sem:
        await process_conversation(session, row, writer)


async def archive_turn_chats(source):
    sema = asyncio.Semaphore(CONCURRENCY)

    reader = csv.DictReader(source)

    with open(OUTPUT_FILE, "w", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=reader.fieldnames
            + ["last_message_id", "wait_for_helpdesk", "helpdesk_timeout", "action"],
        )
        writer.writeheader()

        async with aiohttp.ClientSession() as session:
            tasks = []
            for row in reader:
                tasks.append(bounded_process_conversation(session, row, writer, sema))

            await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(archive_turn_chats(sys.stdin))
