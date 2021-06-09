"""
Looks for any failed requests, and retries them
"""
import asyncio
import json
import sys

import aiohttp

CONCURRENCY = 20


async def request(session, url, method, headers, data, target):
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

        return response_body


async def bounded_retry(session, url, method, headers, data, target, sem):
    async with sem:
        await request(session, url, method, headers, data, target)


async def retry_all(source, target):
    sema = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for row in source:
            row = json.loads(row)
            status = row["response"]["status"]
            if status < 200 or status >= 300:
                request = row["request"]
                tasks.append(
                    bounded_retry(
                        session,
                        request["url"],
                        request["method"],
                        request["headers"],
                        request["json"],
                        sys.stdout,
                        sema,
                    )
                )
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(retry_all(sys.stdin, sys.stdout))
