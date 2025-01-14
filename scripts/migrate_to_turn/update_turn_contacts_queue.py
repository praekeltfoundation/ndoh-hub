import asyncio
import csv
import os
import sys
from urllib.parse import urljoin

import aiohttp

from scripts.migrate_to_rapidpro.retry_requests import request

WORKER_COUNT = 3

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


async def worker(name, queue):
    while True:
        session, row, target = await queue.get()
        await update_turn_contact_details(session, row, target)
        queue.task_done()


async def main(filename, target):
    queue = asyncio.Queue(WORKER_COUNT)

    reader = csv.DictReader(open(filename))
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(WORKER_COUNT):
            task = asyncio.create_task(worker(f"worker-{i}", queue))
            tasks.append(task)

        for row in reader:
            update = (session, row, target)
            await queue.put(update)

        await queue.join()
        for task in tasks:
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    filename = sys.argv[1]
    asyncio.run(main(filename, sys.stdout))
