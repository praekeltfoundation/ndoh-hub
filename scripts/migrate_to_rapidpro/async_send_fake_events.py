import asyncio
import os
import sys
import string
import random
import time
import hmac
import json
import base64
from hashlib import sha256

import aiohttp
from retry_requests import request

TOTAL_EVENTS = 100
CONCURRENCY = 20
HUB_MSG_URL = "https://hub.qa.momconnect.co.za/api/v2/messages/"
# HUB_MSG_URL = "http://localhost:8000/api/v2/messages/"


async def send_event(session, event_id, target):
    print(f"Sending: {event_id}")

    data = {
        "statuses": [
            {
                "id": event_id,
                "recipient_id": "27836378531",
                "status": "failed",
                "timestamp": str(int(time.time()))
            }
        ]
    }

    key = os.environ["TURN_HMAC_SECRET"]
    hmac_data = json.dumps(data, ensure_ascii=False)
    hmac_data = hmac_data.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    h = hmac.new(key.encode(), hmac_data.encode('ascii'), sha256)

    headers = {
        "Authorization": f"TOKEN {os.environ['HUB_TOKEN']}",
        "Content-Type": "application/json",
        "X-Turn-Hook-Subscription": "whatsapp",
        "X-Turn-Hook-Signature": base64.b64encode(h.digest()).decode()
    }

    await request(session, HUB_MSG_URL, "POST", headers, data, target)


async def bounded_send_event(session, event_id, target, sem):
    async with sem:
        await send_event(session, event_id, target)


async def archive_turn_chats(target):
    sema = asyncio.Semaphore(CONCURRENCY)

    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(10))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(TOTAL_EVENTS):
            event_id = f"{result_str}_{i}"
            tasks.append(bounded_send_event(session, event_id, target, sema))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(archive_turn_chats(sys.stdout))
