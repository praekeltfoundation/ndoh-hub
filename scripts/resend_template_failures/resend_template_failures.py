import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import aiohttp

"""
Guide:
1. Run query below to get csv, It gets the last failed template send per contact since
   31 Jan when the payment issue started.
2. Run script:
   `python resend_template_failures.py example.csv > output.json`
3. Check output:
   `jq .response.status output.json | sort | uniq -c`
4. Retry:
   `cat output.json|python scripts/migrate_to_rapidpro/retry_requests.py > output2.json`
5. Repeat last two steps until there are only 200s returned by turn.
"""

WORKER_COUNT = 3

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"


async def send_whatsapp_template(session, wa_id, template_data, target):
    url = urljoin(TURN_URL, "v1/messages")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "application/json",
    }
    data = {"to": wa_id, "type": "template", "template": template_data}
    status, reset_time = await request(session, url, "POST", headers, data, target)

    if status == 429:
        sleep_until(reset_time)
        await send_whatsapp_template(session, wa_id, data, target)


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
        session, wa_id, template_data, target = await queue.get()
        await send_whatsapp_template(session, wa_id, template_data, target)
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
            wa_id = row["contact_id"]
            template_data = json.loads(
                row["template"]
                .replace("'", '"')
                .replace('u"', '"')
                .replace("None", "null")
            )
            update = (session, wa_id, template_data, target)
            await queue.put(update)

        await queue.join()
        for task in tasks:
            task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    filename = sys.argv[1]
    asyncio.run(main(filename, sys.stdout))

"""
Query for CSV(seed hub/eventstore):
===================================
SELECT *
FROM
  (
  SELECT
          eventstore_message.contact_id,
          eventstore_message.data->'template' as template,
          row_number() OVER (PARTITION BY eventstore_message.contact_id
                             ORDER BY eventstore_message.timestamp DESC) AS message_rank
  FROM eventstore_message,
        eventstore_event
  WHERE eventstore_message.TIMESTAMP >= '2025-01-31'
     and eventstore_message.TYPE = 'template'
     AND eventstore_message.id = eventstore_event.message_id
     AND eventstore_event.status = 'failed'
     AND (eventstore_event.data->'errors'->>0)::json->>'code' = '131042'
  ORDER BY eventstore_message.timestamp ASC
  ) AS all_template_sends
WHERE message_rank = 1
"""
