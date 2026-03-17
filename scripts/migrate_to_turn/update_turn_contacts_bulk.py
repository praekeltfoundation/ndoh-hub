import argparse
import csv
import io
import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"
DEFAULT_MAX_BYTES = 950_000


def normalize_urn(value):
    if value is None:
        return value

    urn = str(value).strip()
    if not urn:
        return urn

    if urn.startswith("+"):
        return urn

    if urn.startswith("whatsapp:"):
        urn = urn.split(":", 1)[1].strip()

    if urn.isdigit():
        return f"+{urn}"

    return urn


def serialize_csv_line(values):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(values)
    return buffer.getvalue()


def get_chunk_path(output_dir, source_path, chunk_number):
    return output_dir / f"{source_path.stem}.part{chunk_number:05d}{source_path.suffix}"


def split_csv_file(filename, output_dir=None, max_bytes=DEFAULT_MAX_BYTES):
    source_path = Path(filename)
    output_dir = Path(output_dir or f"{source_path.stem}_chunks")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.jsonl"
    chunks = []

    with source_path.open(newline="") as source_file:
        reader = csv.DictReader(source_file)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError(f"{filename} does not contain a CSV header")

        header_line = serialize_csv_line(fieldnames)
        header_size = len(header_line.encode("utf-8"))

        if header_size >= max_bytes:
            raise ValueError(
                f"CSV header is {header_size} bytes which exceeds the limit of {max_bytes}"
            )

        chunk_file = None
        chunk_path = None
        chunk_size = 0
        chunk_rows = 0

        def start_chunk(chunk_number):
            nonlocal chunk_file, chunk_path, chunk_size, chunk_rows
            chunk_path = get_chunk_path(output_dir, source_path, chunk_number)
            chunk_file = chunk_path.open("w", newline="")
            chunk_file.write(header_line)
            chunk_size = header_size
            chunk_rows = 0

        def finish_chunk():
            nonlocal chunk_file, chunk_path, chunk_size, chunk_rows
            if not chunk_file or not chunk_path:
                return
            chunk_file.close()
            if chunk_rows == 0:
                chunk_path.unlink(missing_ok=True)
                return
            chunks.append(
                {
                    "chunk_number": len(chunks) + 1,
                    "path": str(chunk_path),
                    "rows": chunk_rows,
                    "size_bytes": chunk_size,
                }
            )

        start_chunk(1)

        for row in reader:
            row_values = [row.get(fieldname, "") for fieldname in fieldnames]
            if "urn" in fieldnames:
                urn_index = fieldnames.index("urn")
                row_values[urn_index] = normalize_urn(row_values[urn_index])

            row_line = serialize_csv_line(row_values)
            row_size = len(row_line.encode("utf-8"))

            if header_size + row_size > max_bytes:
                raise ValueError(
                    "A single row is too large for the configured upload limit: "
                    f"{header_size + row_size} bytes required, {max_bytes} allowed"
                )

            if chunk_rows > 0 and chunk_size + row_size > max_bytes:
                finish_chunk()
                start_chunk(len(chunks) + 1)

            chunk_file.write(row_line)
            chunk_rows += 1
            chunk_size += row_size

        finish_chunk()

    with manifest_path.open("w") as manifest_file:
        for chunk in chunks:
            manifest_file.write(json.dumps(chunk))
            manifest_file.write("\n")

    return chunks


def upload_chunk(chunk_path, results_dir):
    url = urljoin(TURN_URL, "v1/contacts")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "text/csv",
    }
    with open(chunk_path, "rb") as data:
        response = requests.post(url, data=data, headers=headers, timeout=300)

    result_path = results_dir / f"{Path(chunk_path).name}.response.csv"
    result_path.write_bytes(response.content)

    return {
        "chunk_path": str(chunk_path),
        "status_code": response.status_code,
        "result_path": str(result_path),
    }


def bulk_update_turn_contacts(
    filename,
    output_dir=None,
    max_bytes=DEFAULT_MAX_BYTES,
    split_only=False,
    stop_on_error=True,
):
    chunks = split_csv_file(filename, output_dir=output_dir, max_bytes=max_bytes)
    print(f"Created {len(chunks)} chunks", flush=True)

    if split_only:
        return chunks

    output_dir = Path(output_dir or f"{Path(filename).stem}_chunks")
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    upload_results = []
    for chunk in chunks:
        result = upload_chunk(chunk["path"], results_dir)
        upload_results.append(result)
        print(
            f"{result['status_code']} {result['chunk_path']} -> {result['result_path']}",
            flush=True,
        )
        if stop_on_error and result["status_code"] >= 400:
            break

    upload_manifest_path = output_dir / "upload_results.jsonl"
    with upload_manifest_path.open("w") as upload_manifest:
        for result in upload_results:
            upload_manifest.write(json.dumps(result))
            upload_manifest.write("\n")

    return upload_results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Split a contacts CSV into Turn-safe chunks and upload sequentially."
    )
    parser.add_argument("filename")
    parser.add_argument("--output-dir")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--split-only", action="store_true")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue uploading remaining chunks after an HTTP error.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    started_at = time.perf_counter()
    bulk_update_turn_contacts(
        args.filename,
        output_dir=args.output_dir,
        max_bytes=args.max_bytes,
        split_only=args.split_only,
        stop_on_error=not args.continue_on_error,
    )
    total_elapsed = time.perf_counter() - started_at
    print(f"Total runtime: {total_elapsed:.2f}s", flush=True)
