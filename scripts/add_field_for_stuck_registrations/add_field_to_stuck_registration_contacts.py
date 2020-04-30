import argparse
import asyncio
import csv
import sys

from ndoh_hub.utils import rapidpro


def process(contact_id):
    contact = rapidpro.get_contacts(uuid=contact_id).first()
    params = {"stuck_in_consent_state": "True"}
    rapidpro.update_contact(contact, fields=params)


async def process_csv(args):
    reader = csv.reader(sys.stdin)
    for row in reader:
        process(row)


def main():
    parser = argparse.ArgumentParser(
        description="Add field to stuck contacts consent state"
    )
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_csv(args))


if __name__ == "__main__":
    main()
