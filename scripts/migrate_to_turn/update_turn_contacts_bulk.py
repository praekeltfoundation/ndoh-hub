import argparse
import csv
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"
DEFAULT_MAX_BYTES = 950_000
MANIFEST_FILENAME = "manifest.jsonl"
SUCCEEDED_STATUS = "succeeded"
PENDING_STATUS = "pending"
FAILED_STATUS = "failed"
IN_PROGRESS_STATUS = "in_progress"


def get_iso_timestamp():
    return datetime.now(timezone.utc).isoformat()


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


def get_output_dir(filename, output_dir=None):
    source_path = Path(filename)
    return Path(output_dir or f"{source_path.stem}_chunks")


def get_manifest_path(output_dir):
    return output_dir / MANIFEST_FILENAME


def get_chunk_path(output_dir, source_path, chunk_number):
    return output_dir / f"{source_path.stem}.part{chunk_number:05d}{source_path.suffix}"


def build_chunk_record(chunk_number, chunk_path, row_count, chunk_size):
    return {
        "chunk_number": chunk_number,
        "path": str(chunk_path),
        "rows": row_count,
        "size_bytes": chunk_size,
        "status": PENDING_STATUS,
        "attempt_count": 0,
        "last_attempted_at": None,
        "status_code": None,
        "result_path": None,
        "error": None,
    }


def write_manifest(manifest_path, chunks):
    with manifest_path.open("w") as manifest_file:
        for chunk in chunks:
            manifest_file.write(json.dumps(chunk))
            manifest_file.write("\n")


def load_manifest(manifest_path):
    with manifest_path.open() as manifest_file:
        chunks = [json.loads(line) for line in manifest_file if line.strip()]

    for chunk in chunks:
        chunk.setdefault("status", PENDING_STATUS)
        chunk.setdefault("attempt_count", 0)
        chunk.setdefault("last_attempted_at", None)
        chunk.setdefault("status_code", None)
        chunk.setdefault("result_path", None)
        chunk.setdefault("error", None)
        if chunk["status"] == IN_PROGRESS_STATUS:
            chunk["status"] = FAILED_STATUS
            if not chunk["error"]:
                chunk["error"] = (
                    "Previous run interrupted while this chunk was in progress."
                )

    return chunks


def split_csv_file(filename, output_dir=None, max_bytes=DEFAULT_MAX_BYTES):
    source_path = Path(filename)
    output_dir = get_output_dir(filename, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = get_manifest_path(output_dir)
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
                build_chunk_record(
                    chunk_number=len(chunks) + 1,
                    chunk_path=chunk_path,
                    row_count=chunk_rows,
                    chunk_size=chunk_size,
                )
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

    write_manifest(manifest_path, chunks)
    return chunks


def ensure_chunks(
    filename, output_dir=None, max_bytes=DEFAULT_MAX_BYTES, rechunk=False
):
    output_dir = get_output_dir(filename, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = get_manifest_path(output_dir)

    if manifest_path.exists() and not rechunk:
        chunks = load_manifest(manifest_path)
        write_manifest(manifest_path, chunks)
        print(f"Loaded {len(chunks)} chunks from {manifest_path}", flush=True)
        return chunks

    chunks = split_csv_file(filename, output_dir=output_dir, max_bytes=max_bytes)
    print(f"Created {len(chunks)} chunks", flush=True)
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
        "status_code": response.status_code,
        "result_path": str(result_path),
    }


def should_upload_chunk(chunk, retry_failed=False):
    if chunk["status"] == SUCCEEDED_STATUS:
        return False
    if retry_failed:
        return chunk["status"] == FAILED_STATUS
    return chunk["status"] in {PENDING_STATUS, FAILED_STATUS}


def bulk_update_turn_contacts(
    filename,
    output_dir=None,
    max_bytes=DEFAULT_MAX_BYTES,
    split_only=False,
    stop_on_error=True,
    retry_failed=False,
    rechunk=False,
):
    output_dir = get_output_dir(filename, output_dir)
    chunks = ensure_chunks(
        filename,
        output_dir=output_dir,
        max_bytes=max_bytes,
        rechunk=rechunk,
    )

    if split_only:
        return None

    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = get_manifest_path(output_dir)

    for chunk in chunks:
        if not should_upload_chunk(chunk, retry_failed=retry_failed):
            continue

        chunk["status"] = IN_PROGRESS_STATUS
        chunk["attempt_count"] += 1
        chunk["last_attempted_at"] = get_iso_timestamp()
        chunk["error"] = None
        write_manifest(manifest_path, chunks)

        try:
            result = upload_chunk(Path(chunk["path"]), results_dir)
        except requests.RequestException as exc:
            chunk["status"] = FAILED_STATUS
            chunk["status_code"] = None
            chunk["result_path"] = None
            chunk["error"] = str(exc)
            write_manifest(manifest_path, chunks)
            print(f"ERROR {chunk['path']} -> {exc}", flush=True)
            if stop_on_error:
                break
            continue

        chunk["status_code"] = result["status_code"]
        chunk["result_path"] = result["result_path"]
        chunk["status"] = (
            SUCCEEDED_STATUS if result["status_code"] < 400 else FAILED_STATUS
        )
        chunk["error"] = None if result["status_code"] < 400 else "HTTP error"
        write_manifest(manifest_path, chunks)

        print(
            f"{chunk['status_code']} {chunk['path']} -> {chunk['result_path']}",
            flush=True,
        )

        if stop_on_error and chunk["status"] == FAILED_STATUS:
            break


def parse_args():
    parser = argparse.ArgumentParser(
        description="Split a contacts CSV into Turn-safe chunks and upload sequentially."
    )
    parser.add_argument("filename")
    parser.add_argument("--output-dir")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--split-only", action="store_true")
    parser.add_argument("--rechunk", action="store_true")
    parser.add_argument(
        "--retry-failed-only",
        action="store_true",
        help="Upload only chunks marked failed in the manifest.",
    )
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
        retry_failed=args.retry_failed_only,
        rechunk=args.rechunk,
    )
    total_elapsed = time.perf_counter() - started_at
    print(f"Total runtime: {total_elapsed:.2f}s", flush=True)
