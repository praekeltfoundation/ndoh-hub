import csv
import json

import pytest

from scripts.migrate_to_turn.update_turn_contacts_bulk import split_csv_file


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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

    manifest_path = tmp_path / "chunks" / "manifest.jsonl"
    manifest_rows = [
        json.loads(line) for line in manifest_path.read_text().splitlines() if line
    ]
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
