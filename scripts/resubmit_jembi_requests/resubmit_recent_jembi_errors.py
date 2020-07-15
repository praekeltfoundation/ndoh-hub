import time

import psycopg2
import requests
from requests.exceptions import HTTPError, RequestException

ORG_ID = 5
RESUBMIT_DAYS = 3

JEMBI_AUTH = ""

DB = {
    "dbname": "ndoh_rapidpro",
    "user": "ndoh_rapidpro",
    "port": 7000,
    "host": "localhost",
    "password": "",
}

if __name__ == "__main__":
    conn = psycopg2.connect(**DB)

    cursor = conn.cursor("webhook_errors")

    cursor.execute(
        """
        SELECT id, url, request, status_code, contact_id, date_trunc('day', created_on)
        FROM api_webhookresult
        WHERE org_id = %s
        AND status_code NOT IN (202)
        AND url LIKE '%%jembi%%'
        AND created_on >= now()::date - interval '%s days'
        ORDER BY created_on ASC
        """,
        (ORG_ID, RESUBMIT_DAYS),
    )

    total = 0
    start, d_print = time.time(), time.time()

    webhook_calls = []
    failed_again = []
    for (request_id, url, request, status_code, contact_id, day) in cursor:
        day = str(day).split(" ")[0]
        key = f"{url}_{contact_id}_{day}"

        if key in webhook_calls:
            continue

        webhook_calls.append(key)

        body = request.split("\n")[-1]

        try:
            r = requests.post(
                url=url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {JEMBI_AUTH}",
                },
                data=body,
                verify=False,
            )
            r.raise_for_status()
        except (RequestException, HTTPError):
            failed_again.append(request_id)

        if time.time() - d_print > 1:
            print(  # noqa
                f"\rProcessed {total}"
                f" webhooks at {total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()

        total += 1

    print("")  # noqa
    print(f"Processed: {total}")  # noqa
    print(f"Failed again: {failed_again}")  # noqa
