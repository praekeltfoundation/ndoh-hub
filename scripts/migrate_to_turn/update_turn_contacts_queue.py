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


def log_message(message):
    print(message, file=sys.stderr, flush=True)


def format_reset_time(reset_time):
    target = datetime.fromtimestamp(int(str(reset_time).split(".")[0]))
    return target.strftime("%Y-%m-%d %H:%M:%S")


async def update_turn_contact_details(session, wa_id, data, target):
    url = urljoin(TURN_URL, f"/v1/contacts/{wa_id}/profile")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "application/json",
        "Accept": "application/vnd.v1+json",
    }
    status, reset_time = await request(session, url, "PATCH", headers, data, target)

    if status == 429:
        log_message(
            f"Rate limit hit. Waiting until {format_reset_time(reset_time)}"
        )
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
    overall_started_at = time.perf_counter()

    reader = csv.DictReader(open(filename))
    row_count = 0
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(WORKER_COUNT):
            task = asyncio.create_task(worker(f"worker-{i}", queue))
            tasks.append(task)

        for row in reader:
            wa_id = row.pop("urn")
            update = (session, wa_id, row, target)
            await queue.put(update)
            row_count += 1

        log_message(
            f"Queued {row_count} contacts from {filename} with {WORKER_COUNT} workers"
        )
        await queue.join()
        for task in tasks:
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    total_elapsed = time.perf_counter() - overall_started_at
    log_message(
        f"Processed {row_count} contacts from {filename} in {total_elapsed:.2f}s"
    )


if __name__ == "__main__":
    filename = sys.argv[1]
    asyncio.run(main(filename, sys.stdout))
