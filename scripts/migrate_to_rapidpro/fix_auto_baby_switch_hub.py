import asyncio
import csv
import json
import os
import sys

import aiohttp
from retry_requests import request
from six.moves import urllib_parse

CONCURRENCY = 20
HUB_URL = "https://hub.qa.momconnect.co.za"
HUB_TOKEN = os.environ["HUB_TOKEN"]

JEMBI_OUTPUT_FILE = "jembi_babyswitches.csv"


async def process_babyswitch(session, row, target, jembi_writer):
    contact_id = row["contact_id"]
    timestamp = row["timestamp"]

    url = urllib_parse.urljoin(HUB_URL, "/api/v2/babyswitches/")
    headers = {
        "Authorization": f"TOKEN {HUB_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "contact_id": contact_id,
        "source": "Automatic (Fix)",
        "timestamp": timestamp,
    }

    response = await request(session, url, "POST", headers, data, target)
    row["event_id"] = json.loads(response)["id"]
    jembi_writer.writerow(row)


async def bounded_process_babyswitch(session, row, target, jembi_writer, sem):
    async with sem:
        await process_babyswitch(session, row, target, jembi_writer)


async def send_babyswitches_to_hub(source, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(source)

    with open(JEMBI_OUTPUT_FILE, "w", newline="") as jembi_target:
        jembi_writer = csv.DictWriter(
            jembi_target, fieldnames=["contact_id", "msisdn", "timestamp", "event_id"]
        )
        jembi_writer.writeheader()
        async with aiohttp.ClientSession() as session:
            tasks = []
            for row in reader:
                tasks.append(
                    bounded_process_babyswitch(session, row, target, jembi_writer, sema)
                )

            await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(send_babyswitches_to_hub(sys.stdin, sys.stdout))
