import os
import asyncio
import csv
import sys
from urllib.parse import urljoin

import aiohttp

from scripts.migrate_to_rapidpro.retry_requests import request


CONCURRENCY = 20

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"


async def update_turn_contact_details(session, row, target):
    wa_id = row.pop("wa_id")

    url = urljoin(TURN_URL, f"/v1/contacts/{wa_id}/profile")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    await request(session, url, "PATCH", headers, row, target)


async def bounded_update_turn_contact_details(session, row, target, sem):
    async with sem:
        await update_turn_contact_details(session, row, target)


async def update_turn_contacts(filename, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(open(filename))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in reader:
            tasks.append(
                bounded_update_turn_contact_details(session, row, target, sema)
            )

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    fliename = sys.argv[1]
    asyncio.run(update_turn_contacts(fliename, sys.stdout))
