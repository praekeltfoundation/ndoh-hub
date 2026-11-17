import asyncio
import csv
import json
import os
import sys
from urllib.parse import urljoin

import aiohttp

CONCURRENCY = 20

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"


async def request_with_status(session, url, method, headers, data, target):
    func = getattr(session, method.lower())
    async with func(url, headers=headers, json=data) as response:
        response_body = await response.text()
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
        return response.status, response_body


async def get_turn_contact_details(session, row, target):
    wa_id = row["urn"]

    profile_url = urljoin(TURN_URL, f"/v1/contacts/{wa_id}/profile")
    base_headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "Accept": "application/vnd.v1+json",
    }
    status, _ = await request_with_status(
        session, profile_url, "GET", base_headers, None, target
    )
    if status == 404:
        create_url = urljoin(TURN_URL, f"/v1/contacts/{wa_id}")
        create_headers = {
            **base_headers,
            "Content-Type": "application/json",
        }
        await request_with_status(
            session, create_url, "POST", create_headers, {}, target
        )


async def bounded_get_turn_contact_details(session, row, target, sem):
    async with sem:
        await get_turn_contact_details(session, row, target)


async def get_turn_contacts(filename, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    reader = csv.DictReader(open(filename))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in reader:
            tasks.append(bounded_get_turn_contact_details(session, row, target, sema))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    filename = sys.argv[1]
    asyncio.run(get_turn_contacts(filename, sys.stdout))
