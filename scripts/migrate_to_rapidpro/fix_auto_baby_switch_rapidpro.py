import asyncio
import csv
import os
import sys

import aiohttp
from retry_requests import request
from six.moves import urllib_parse

CONCURRENCY = 20
RAPIDPRO_URL = "https://rapidpro.prd.momconnect.co.za"
RAPIDPRO_TOKEN = os.environ["RAPIDPRO_TOKEN"]


async def process_contact(session, row, target):
    contact_id = row["contact_id"]
    baby_dob_field = row["baby_dob_field"]
    baby_dob = row["baby_dob"]

    url = urllib_parse.urljoin(RAPIDPRO_URL, f"/api/v2/contacts.json?uuid={contact_id}")
    headers = {
        "Authorization": f"TOKEN {RAPIDPRO_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "fields": {
            "prebirth_messaging": "",
            "postbirth_messaging": "TRUE",
            baby_dob_field: baby_dob,
        }
    }

    await request(session, url, "POST", headers, data, target)


async def bounded_process_contact(session, row, target, sem):
    async with sem:
        await process_contact(session, row, target)


async def update_rapidpro_contacts(source, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(source)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in reader:
            tasks.append(bounded_process_contact(session, row, target, sema))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(update_rapidpro_contacts(sys.stdin, sys.stdout))
