import asyncio
import csv
import os
import sys
from datetime import datetime

import aiohttp
from retry_requests import request
from six.moves import urllib_parse

CONCURRENCY = 20
JEMBI_URL = "https://momconnect.openhim.dhmis.org:5000/ws/rest/v1"
JEMBI_TOKEN = os.environ["JEMBI_TOKEN"]


async def process_babyswitch(session, row, target):
    contact_id = row["contact_id"]
    timestamp = datetime.fromisoformat(row["timestamp"]).strftime("%Y%m%d%H%M%S")
    event_id = row["event_id"]
    msisdn = row["msisdn"]

    url = urllib_parse.urljoin(JEMBI_URL, "/subscription/")
    headers = {
        "Authorization": f"Basic {JEMBI_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "encdate": timestamp,
        "mha": 1,
        "swt": 1,
        "cmsisdn": msisdn,
        "dmsisdn": msisdn,
        "sid": contact_id,
        "eid": event_id,
        "type": 11,
    }

    await request(session, url, "POST", headers, data, target)


async def bounded_process_babyswitch(session, row, target, sem):
    async with sem:
        await process_babyswitch(session, row, target)


async def send_babyswitches_to_jembi(source, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(source)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in reader:
            tasks.append(bounded_process_babyswitch(session, row, target, sema))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(send_babyswitches_to_jembi(sys.stdin, sys.stdout))
