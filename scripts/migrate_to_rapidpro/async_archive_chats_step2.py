import asyncio
import csv
import os
import sys

import aiohttp
from retry_requests import request
from six.moves import urllib_parse

CONCURRENCY = 20
TURN_URL = "https://whatsapp.praekelt.org"
RAPIDPRO_URL = "https://rapidpro.prd.momconnect.co.za"


async def process_conversation(session, row, target):
    whatsapp_id = str(row["owner"]).replace("+", "")
    last_message_id = row["last_message_id"]

    url = None
    if row["action"] == "ARCHIVE":
        url = urllib_parse.urljoin(TURN_URL, f"v1/chats/{whatsapp_id}/archive")
        headers = {
            "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
            "Accept": "application/vnd.v1+json",
            "Content-Type": "application/json",
        }
        data = {"before": last_message_id, "reason": "Bulk archived"}
    else:
        url = urllib_parse.urljoin(
            RAPIDPRO_URL, f"/api/v2/contacts.json?urn=whatsapp:{whatsapp_id}"
        )
        headers = {
            "Authorization": f"TOKEN {os.environ['RAPIDPRO_TOKEN']}",
            "Content-Type": "application/json",
        }
        data = {
            "fields": {
                "wait_for_helpdesk": row["wait_for_helpdesk"],
                "helpdesk_message_id": row["last_message_id"],
                "helpdesk_timeout": row["helpdesk_timeout"],
            }
        }

    await request(session, url, "POST", headers, data, target)


async def bounded_process_conversation(session, row, target, sem):
    async with sem:
        await process_conversation(session, row, target)


async def archive_turn_chats(source, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(source)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in reader:
            tasks.append(bounded_process_conversation(session, row, target, sema))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(archive_turn_chats(sys.stdin, sys.stdout))
