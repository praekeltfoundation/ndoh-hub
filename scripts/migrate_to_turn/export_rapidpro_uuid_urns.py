import argparse
import csv
import os
import time
from datetime import datetime
from pathlib import Path

from temba_client.exceptions import TembaConnectionError
from temba_client.v2 import TembaClient

ENV = "prd"  # qa or prd
RAPIDPRO_URL = f"https://rapidpro.{ENV}.momconnect.co.za"
OUTPUT_FIELDNAMES = ["contact_id", "urn"]
DEFAULT_MAX_RETRIES = 8
DEFAULT_BACKOFF_SECONDS = 2


def get_readable_timestamp(dt=None):
    dt = dt or datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def log(message):
    print(f"[{get_readable_timestamp()}] {message}")


def get_wa_id(contact):
    for urn in contact.urns:
        if urn.startswith("whatsapp:"):
            return urn.split(":", 1)[1]

    return None


def get_output_filename(output_filename=None):
    if output_filename:
        return Path(output_filename)

    return Path(f"rapidpro_uuid_urns_{ENV}.csv")


def iter_contact_batches(
    client,
    max_retries=DEFAULT_MAX_RETRIES,
    backoff_seconds=DEFAULT_BACKOFF_SECONDS,
):
    resume_cursor = None
    retries = 0
    iterator = client.get_contacts().iterfetches(
        retry_on_rate_exceed=True,
        resume_cursor=resume_cursor,
    )

    while True:
        try:
            contact_batch = next(iterator)
            resume_cursor = iterator.get_cursor()
            retries = 0
            yield contact_batch
        except StopIteration:
            return
        except TembaConnectionError:
            retries += 1
            if retries > max_retries:
                raise

            sleep_seconds = backoff_seconds * (2 ** (retries - 1))
            log(
                "RapidPro connection error. "
                f"Retry {retries}/{max_retries} in {sleep_seconds}s"
            )
            time.sleep(sleep_seconds)
            iterator = client.get_contacts().iterfetches(
                retry_on_rate_exceed=True,
                resume_cursor=resume_cursor,
            )


def export_rapidpro_uuid_urns(
    client,
    output_filename=None,
    max_retries=DEFAULT_MAX_RETRIES,
    backoff_seconds=DEFAULT_BACKOFF_SECONDS,
):
    output_path = get_output_filename(output_filename)
    run_start = datetime.now().astimezone()
    rows_written = 0
    rows_skipped = 0

    log(f"Starting RapidPro UUID/URN export to {output_path}")

    with output_path.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()

        for batch_number, contact_batch in enumerate(
            iter_contact_batches(
                client,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            ),
            start=1,
        ):
            log(
                f"Processing contact_batch #{batch_number} - wrote {rows_written}, skipped {rows_skipped}"
            )

            for contact in contact_batch:
                wa_id = get_wa_id(contact)
                if not wa_id:
                    rows_skipped += 1
                    continue

                writer.writerow(
                    {
                        "contact_id": contact.uuid,
                        "urn": wa_id,
                    }
                )
                rows_written += 1

    run_end = datetime.now().astimezone()
    log("Finished RapidPro UUID/URN export")
    log(f"Run started: {get_readable_timestamp(run_start)}")
    log(f"Run ended: {get_readable_timestamp(run_end)}")
    log(f"Rows written: {rows_written}")
    log(f"Rows skipped: {rows_skipped}")
    log(f"Output file: {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export RapidPro contact UUIDs and WhatsApp URNs to a CSV."
    )
    parser.add_argument("--output")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument(
        "--backoff-seconds",
        type=int,
        default=DEFAULT_BACKOFF_SECONDS,
        help="Initial backoff in seconds for RapidPro connection retries.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rapidpro_client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])
    export_rapidpro_uuid_urns(
        rapidpro_client,
        output_filename=args.output,
        max_retries=args.max_retries,
        backoff_seconds=args.backoff_seconds,
    )
