import argparse
import csv
import sys
from temba_client.v2 import TembaClient
import environ

rapidpro = TembaClient(environ["RAPIDPRO_URL"], environ["RAPIDPRO_TOKEN"])


def process(contact_id):
    params = {"stuck_in_consent_state": "True"}
    rapidpro.update_contact(contact_id, fields=params)


async def process_csv(args):
    reader = csv.reader(sys.stdin)
    for row in reader:
        process(row)


def main():
    parser = argparse.ArgumentParser(
        description="Add field to stuck contacts consent state"
    )
    args = parser.parse_args()
    process_csv(args)


if __name__ == "__main__":
    main()
