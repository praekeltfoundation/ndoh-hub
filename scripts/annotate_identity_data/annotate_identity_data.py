import django

import argparse
import asyncio
import csv
from requests.exceptions import RequestException
import sys


django.setup()


def fetch(msisdn, row, fields):
    from ndoh_hub.utils import is_client
    from registrations.models import Registration

    try:
        identity = next(is_client.get_identity_by_address("msisdn", msisdn)["results"])
        identity_id = identity["id"]
    except (StopIteration, RequestException):
        identity_id = None

    registration = (
        Registration.objects.filter(registrant_id=identity_id)
        .order_by("-created_at")
        .first()
    )
    for field in fields:
        if registration is None:
            row[field] = None
        else:
            row[field] = registration.data.get(field)
    return row


async def process_csv(args):
    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, reader.fieldnames + args.annotate)
    writer.writeheader()

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, fetch, *(row[args.source], row, args.annotate))
        for row in reader
    ]

    for row in await asyncio.gather(*tasks):
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Annotate identity data")
    parser.add_argument(
        "--source",
        "-s",
        default="phone_number",
        help=(
            "The field in the input CSV to find the phone numbers to look up the "
            "identities with"
        ),
    )
    parser.add_argument(
        "--annotate",
        "-a",
        nargs="+",
        default=[],
        help="The registration detail fields to annotate onto the CSV",
    )
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_csv(args))


if __name__ == "__main__":
    main()
