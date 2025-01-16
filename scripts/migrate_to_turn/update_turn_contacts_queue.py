import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import aiohttp

WORKER_COUNT = 3

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"


async def update_turn_contact_details(session, wa_id, data, target):
    url = urljoin(TURN_URL, f"/v1/contacts/{wa_id}/profile")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    status, reset_time = await request(session, url, "PATCH", headers, data, target)

    if status == 429:
        sleep_until(reset_time)
        await update_turn_contact_details(session, wa_id, data, target)


def sleep_until(reset_time):
    target = datetime.fromtimestamp(int(str(reset_time).split(".")[0]))
    delta = target - datetime.now()
    if delta > timedelta(0):
        time.sleep(delta.total_seconds())
        return True


async def request(session, url, method, headers, data, target):
    func = getattr(session, method.lower())
    async with func(url, headers=headers, json=data) as response:
        response_body = await response.text()

        if response.status == 429:
            return response.status, response.headers["x-ratelimit-reset"]

        request_data = {
            "request": {
                "url": response.request_info.url.human_repr(),
                "method": response.request_info.method,
                "headers": dict(response.request_info.headers),
                "json": data,
            },
            "response": {
                "status": response.status,
                "headers": dict(response.headers),
                "body": response_body,
            },
        }

        target.write(json.dumps(request_data))
        target.write("\n")

        return response.status, None


async def worker(name, queue):
    while True:
        session, wa_id, data, target = await queue.get()
        await update_turn_contact_details(session, wa_id, data, target)
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
            wa_id = row.pop("urn")
            update = (session, wa_id, row, target)
            await queue.put(update)

        await queue.join()
        for task in tasks:
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    filename = sys.argv[1]
    asyncio.run(main(filename, sys.stdout))
