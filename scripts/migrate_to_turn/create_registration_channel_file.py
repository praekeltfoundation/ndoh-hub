import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

from temba_client.v2 import TembaClient

ENV = "prd"  # qa or prd
RAPIDPRO_URL = f"https://rapidpro.{ENV}.momconnect.co.za"
OUTPUT_FIELDNAMES = ["urn", "reg_channel"]
DEFAULT_WORKER_COUNT = 5


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


def get_reg_channel(source):
    normalized = str(source or "").strip().lower()
    # TODO: figure out what we put here
    if "whatsapp" in normalized:
        return "whatsapp"
    return "ussd"


def get_rapidpro_contact(client, contact_id):
    return client.get_contacts(uuid=contact_id).first(retry_on_rate_exceed=True)


def get_output_filename(input_filename, output_filename=None):
    if output_filename:
        return Path(output_filename)

    input_path = Path(input_filename)
    return input_path.with_name(f"{input_path.stem}_turn.csv")


def build_output_row(contact, source):
    wa_id = get_wa_id(contact)
    if not wa_id:
        return None

    return {
        "urn": wa_id,
        "reg_channel": get_reg_channel(source),
    }


def build_output_row_from_urn(urn, source):
    if not urn:
        return None

    return {
        "urn": urn,
        "reg_channel": get_reg_channel(source),
    }


def process_input_row(client, row):
    contact_id = str(row.get("contact_id", "")).strip()
    source = row.get("source", "")

    contact = get_rapidpro_contact(client, contact_id)
    if not contact:
        return {
            "status": "skipped",
            "contact_id": contact_id,
            "reason": "RapidPro contact not found",
        }

    output_row = build_output_row(contact, source)
    if not output_row:
        return {
            "status": "skipped",
            "contact_id": contact_id,
            "reason": "RapidPro contact has no WhatsApp URN",
        }

    return {"status": "written", "output_row": output_row}


def load_uuid_urn_lookup(filename):
    lookup = {}

    with Path(filename).open(newline="") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            contact_id = str(row.get("contact_id", "")).strip()
            urn = str(row.get("urn", "")).strip()

            if not contact_id or not urn:
                continue

            lookup[contact_id] = urn

    return lookup


def create_registration_channel_file(
    client,
    input_filename,
    output_filename=None,
    worker_count=DEFAULT_WORKER_COUNT,
    uuid_urn_lookup=None,
):
    input_path = Path(input_filename)
    output_path = get_output_filename(input_filename, output_filename)

    log(f"Starting registration channel export from {input_path}")

    rows_written = 0
    rows_skipped = 0
    processed_rows = 0

    if uuid_urn_lookup is None and worker_count < 1:
        raise ValueError("worker_count must be greater than 0")

    with input_path.open(newline="") as input_file, output_path.open(
        "w", newline=""
    ) as output_file:
        reader = csv.DictReader(input_file)
        output_writer = csv.DictWriter(output_file, fieldnames=OUTPUT_FIELDNAMES)

        output_writer.writeheader()
        if uuid_urn_lookup is not None:
            log(f"Using UUID/URN lookup file with {len(uuid_urn_lookup)} rows")

            for row in reader:
                processed_rows += 1
                contact_id = str(row.get("contact_id", "")).strip()
                source = row.get("source", "")
                urn = uuid_urn_lookup.get(contact_id)

                output_row = build_output_row_from_urn(urn, source)
                if not output_row:
                    log(
                        f"Skipping contact_id={contact_id}: UUID not found in lookup file"
                    )
                    rows_skipped += 1
                    continue

                output_writer.writerow(output_row)
                rows_written += 1

                if processed_rows % 1000 == 0:
                    log(
                        f"Processed {processed_rows} rows, wrote {rows_written}, skipped {rows_skipped}"
                    )
        else:
            from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

            log(f"Using {worker_count} RapidPro lookup workers")

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                pending_futures = set()

                def handle_result(result):
                    nonlocal processed_rows, rows_written, rows_skipped

                    processed_rows += 1

                    if result["status"] == "written":
                        output_writer.writerow(result["output_row"])
                        rows_written += 1
                    else:
                        log(
                            f"Skipping contact_id={result['contact_id']}: {result['reason']}"
                        )
                        rows_skipped += 1

                    if processed_rows % 1000 == 0:
                        log(
                            f"Processed {processed_rows} rows, wrote {rows_written}, skipped {rows_skipped}"
                        )

                for row in reader:
                    pending_futures.add(executor.submit(process_input_row, client, row))

                    if len(pending_futures) >= worker_count * 4:
                        done, pending_futures = wait(
                            pending_futures,
                            return_when=FIRST_COMPLETED,
                        )
                        for future in done:
                            handle_result(future.result())

                while pending_futures:
                    done, pending_futures = wait(
                        pending_futures,
                        return_when=FIRST_COMPLETED,
                    )
                    for future in done:
                        handle_result(future.result())

    log(f"Finished registration channel export from {input_path}")
    log(f"Processed rows: {processed_rows}")
    log(f"Rows written: {rows_written}")
    log(f"Rows skipped: {rows_skipped}")
    log(f"Output file: {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a Turn bulk update CSV from a registration export by looking up "
            "RapidPro contacts via contact UUID."
        )
    )
    parser.add_argument(
        "--uuid-urn-file",
        help=(
            "CSV file with contact_id and urn columns exported from RapidPro. "
            "When provided, this is used instead of live RapidPro lookups."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKER_COUNT,
        help=(
            "Number of concurrent RapidPro lookups to run. "
            "Lower this if you start hitting rate limits."
        ),
    )
    parser.add_argument("filename", help="CSV with contact_id, source and timestamp")
    parser.add_argument("--output")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    uuid_urn_lookup = None
    rapidpro_client = None

    if args.uuid_urn_file:
        uuid_urn_lookup = load_uuid_urn_lookup(args.uuid_urn_file)
    else:
        rapidpro_client = TembaClient(RAPIDPRO_URL, os.environ["RAPIDPRO_TOKEN"])

    create_registration_channel_file(
        rapidpro_client,
        args.filename,
        output_filename=args.output,
        worker_count=args.workers,
        uuid_urn_lookup=uuid_urn_lookup,
    )


"""
Example query for part 1:
with registration_sources as (
    select contact_id, source, timestamp from eventstore_prebirthregistration
    union all
    select contact_id, source, timestamp from eventstore_postbirthregistration
    union all
    select contact_id, source, timestamp from eventstore_chwregistration
),
ranked_sources as (
    select
        contact_id,
        source,
        timestamp,
        row_number() over (
            partition by contact_id
            order by timestamp desc
        ) as row_num
    from registration_sources
),
latest_sources as (
    select contact_id, source, timestamp
    from ranked_sources
    where row_num = 1
),
split_exports as (
    select
        contact_id,
        source,
        timestamp,
        ntile(4) over (order by contact_id) as export_part
    from latest_sources
)
select contact_id, source, timestamp
from split_exports
where export_part = 1;
"""
