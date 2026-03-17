import csv
import json

import pytest

from scripts.migrate_to_turn.update_turn_contacts_bulk import (
    FAILED_STATUS,
    SUCCEEDED_STATUS,
    bulk_update_turn_contacts,
    ensure_chunks,
    split_csv_file,
)


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_split_csv_file_keeps_each_chunk_within_limit(tmp_path):
    csv_path = tmp_path / "contacts.csv"
    fieldnames = ["urn", "name", "note"]
    rows = [
        {"urn": f"2782000{i:04d}", "name": f"User {i}", "note": "x" * 35}
        for i in range(12)
    ]
    write_csv(csv_path, fieldnames, rows)

    chunks = split_csv_file(csv_path, output_dir=tmp_path / "chunks", max_bytes=140)

    assert len(chunks) > 1
    assert sum(chunk["rows"] for chunk in chunks) == len(rows)
    for chunk in chunks:
        assert chunk["size_bytes"] <= 140
        assert chunk["status"] == "pending"
        assert chunk["attempt_count"] == 0

    manifest_path = tmp_path / "chunks" / "manifest.jsonl"
    manifest_rows = read_manifest(manifest_path)
    assert manifest_rows == chunks


def test_split_csv_file_rejects_single_row_that_exceeds_limit(tmp_path):
    csv_path = tmp_path / "contacts.csv"
    write_csv(
        csv_path,
        ["urn", "note"],
        [{"urn": "27820000001", "note": "x" * 500}],
    )

    with pytest.raises(ValueError, match="single row is too large"):
        split_csv_file(csv_path, output_dir=tmp_path / "chunks", max_bytes=100)


def test_split_csv_file_normalizes_urn_to_e164(tmp_path):
    csv_path = tmp_path / "contacts.csv"
    write_csv(
        csv_path,
        ["urn", "name"],
        [
            {"urn": "27820000001", "name": "Digits"},
            {"urn": "whatsapp:27820000002", "name": "Whatsapp"},
            {"urn": "+27820000003", "name": "Plus"},
        ],
    )

    chunks = split_csv_file(csv_path, output_dir=tmp_path / "chunks", max_bytes=1024)

    with open(chunks[0]["path"], newline="") as chunk_file:
        reader = csv.DictReader(chunk_file)
        assert [row["urn"] for row in reader] == [
            "+27820000001",
            "+27820000002",
            "+27820000003",
        ]


def test_ensure_chunks_reuses_existing_manifest_and_marks_stale_in_progress(tmp_path):
    csv_path = tmp_path / "contacts.csv"
    write_csv(
        csv_path,
        ["urn", "name"],
        [{"urn": "27820000001", "name": "One"}],
    )
    output_dir = tmp_path / "chunks"
    split_csv_file(csv_path, output_dir=output_dir, max_bytes=1024)

    manifest_path = output_dir / "manifest.jsonl"
    manifest_rows = read_manifest(manifest_path)
    manifest_rows[0]["status"] = "in_progress"
    manifest_rows[0]["attempt_count"] = 1
    manifest_path.write_text("".join(f"{json.dumps(row)}\n" for row in manifest_rows))

    chunks = ensure_chunks(csv_path, output_dir=output_dir, max_bytes=1024)

    assert chunks[0]["status"] == FAILED_STATUS
    assert "interrupted" in chunks[0]["error"]
    assert read_manifest(manifest_path)[0]["status"] == FAILED_STATUS


def test_bulk_update_turn_contacts_resumes_and_skips_succeeded_chunks(tmp_path, monkeypatch):
    csv_path = tmp_path / "contacts.csv"
    write_csv(
        csv_path,
        ["urn", "name", "note"],
        [
            {"urn": "27820000001", "name": "One", "note": "x" * 40},
            {"urn": "27820000002", "name": "Two", "note": "x" * 40},
            {"urn": "27820000003", "name": "Three", "note": "x" * 40},
            {"urn": "27820000004", "name": "Four", "note": "x" * 40},
        ],
    )
    output_dir = tmp_path / "chunks"
    split_csv_file(csv_path, output_dir=output_dir, max_bytes=120)

    manifest_path = output_dir / "manifest.jsonl"
    manifest_rows = read_manifest(manifest_path)
    manifest_rows[0]["status"] = SUCCEEDED_STATUS
    manifest_rows[0]["status_code"] = 200
    manifest_rows[0]["result_path"] = str(output_dir / "results" / "first.response.csv")
    manifest_path.write_text("".join(f"{json.dumps(row)}\n" for row in manifest_rows))

    uploaded = []

    def fake_upload_chunk(chunk_path, results_dir):
        uploaded.append(chunk_path)
        result_path = results_dir / f"{chunk_path.name}.response.csv"
        result_path.write_text("ok")
        return {"status_code": 200, "result_path": str(result_path)}

    monkeypatch.setattr(
        "scripts.migrate_to_turn.update_turn_contacts_bulk.upload_chunk",
        fake_upload_chunk,
    )

    bulk_update_turn_contacts(csv_path, output_dir=output_dir, max_bytes=120)

    assert len(uploaded) == len(manifest_rows) - 1
    assert str(output_dir / "contacts.part00001.csv") not in uploaded
    final_manifest = read_manifest(manifest_path)
    assert all(chunk["status"] == SUCCEEDED_STATUS for chunk in final_manifest)


def test_bulk_update_turn_contacts_stops_and_persists_failure(tmp_path, monkeypatch):
    csv_path = tmp_path / "contacts.csv"
    write_csv(
        csv_path,
        ["urn", "name", "note"],
        [
            {"urn": "27820000001", "name": "One", "note": "x" * 40},
            {"urn": "27820000002", "name": "Two", "note": "x" * 40},
            {"urn": "27820000003", "name": "Three", "note": "x" * 40},
        ],
    )
    output_dir = tmp_path / "chunks"
    split_csv_file(csv_path, output_dir=output_dir, max_bytes=120)

    def fake_upload_chunk(chunk_path, results_dir):
        result_path = results_dir / f"{chunk_path.name}.response.csv"
        result_path.write_text("failed")
        return {"status_code": 500, "result_path": str(result_path)}

    monkeypatch.setattr(
        "scripts.migrate_to_turn.update_turn_contacts_bulk.upload_chunk",
        fake_upload_chunk,
    )

    bulk_update_turn_contacts(csv_path, output_dir=output_dir, max_bytes=120)
    manifest_rows = read_manifest(output_dir / "manifest.jsonl")
    assert manifest_rows[0]["status"] == FAILED_STATUS
    assert manifest_rows[0]["attempt_count"] == 1
    assert manifest_rows[1]["status"] == "pending"
