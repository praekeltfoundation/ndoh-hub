import csv
from types import SimpleNamespace

from scripts.migrate_to_turn.create_registration_channel_file import (
    create_registration_channel_file,
    get_reg_channel,
    load_uuid_urn_lookup,
)


def read_csv_rows(path):
    with path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


class FakeContactsEndpoint:
    def __init__(self, contact):
        self.contact = contact

    def first(self, retry_on_rate_exceed=True):
        return self.contact


class FakeClient:
    def __init__(self, contacts_by_uuid):
        self.contacts_by_uuid = contacts_by_uuid

    def get_contacts(self, uuid=None):
        return FakeContactsEndpoint(self.contacts_by_uuid.get(uuid))


def test_get_reg_channel_maps_whatsapp_sources():
    assert get_reg_channel("WhatsApp") == "whatsapp"
    assert get_reg_channel("WhatsApp: +27796312456") == "whatsapp"


def test_get_reg_channel_maps_non_whatsapp_sources_to_sms():
    assert get_reg_channel("Clinic USSD") == "ussd"
    assert get_reg_channel("Register timed out contacts") == "ussd"


def test_create_registration_channel_file_writes_turn_bulk_csv(tmp_path):
    input_path = tmp_path / "registration.csv"
    output_path = tmp_path / "registration_turn.csv"

    with input_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["contact_id", "source", "timestamp"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "contact_id": "contact-1",
                    "source": "Clinic USSD",
                    "timestamp": "2025-02-11 10:17",
                },
                {
                    "contact_id": "contact-2",
                    "source": "WhatsApp",
                    "timestamp": "2025-02-11 10:18",
                },
            ]
        )

    client = FakeClient(
        {
            "contact-1": SimpleNamespace(urns=["tel:+27123", "whatsapp:27820000001"]),
            "contact-2": SimpleNamespace(urns=["whatsapp:27820000002"]),
        }
    )

    create_registration_channel_file(
        client,
        input_path,
        output_filename=output_path,
    )

    assert sorted(read_csv_rows(output_path), key=lambda row: row["urn"]) == [
        {"urn": "27820000001", "reg_channel": "ussd"},
        {"urn": "27820000002", "reg_channel": "whatsapp"},
    ]


def test_create_registration_channel_file_skips_when_contact_missing(tmp_path):
    input_path = tmp_path / "registration.csv"
    output_path = tmp_path / "registration_turn.csv"

    with input_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["contact_id", "source", "timestamp"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "contact_id": "missing-contact",
                "source": "Clinic USSD",
                "timestamp": "2025-02-11 10:19",
            }
        )

    client = FakeClient({})

    create_registration_channel_file(client, input_path, output_filename=output_path)

    assert read_csv_rows(output_path) == []


def test_create_registration_channel_file_rejects_invalid_worker_count(tmp_path):
    input_path = tmp_path / "registration.csv"

    with input_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["contact_id", "source", "timestamp"],
        )
        writer.writeheader()

    client = FakeClient({})

    try:
        create_registration_channel_file(client, input_path, worker_count=0)
    except ValueError as exc:
        assert str(exc) == "worker_count must be greater than 0"
    else:
        raise AssertionError("Expected ValueError for invalid worker_count")


def test_load_uuid_urn_lookup_reads_lookup_csv(tmp_path):
    lookup_path = tmp_path / "rapidpro_uuid_urns.csv"

    with lookup_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["contact_id", "urn"])
        writer.writeheader()
        writer.writerows(
            [
                {"contact_id": "contact-1", "urn": "27820000001"},
                {"contact_id": "contact-2", "urn": "27820000002"},
            ]
        )

    assert load_uuid_urn_lookup(lookup_path) == {
        "contact-1": "27820000001",
        "contact-2": "27820000002",
    }


def test_create_registration_channel_file_uses_uuid_urn_lookup(tmp_path):
    input_path = tmp_path / "registration.csv"
    output_path = tmp_path / "registration_turn.csv"
    lookup = {
        "contact-1": "27820000001",
        "contact-2": "27820000002",
    }

    with input_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["contact_id", "source", "timestamp"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "contact_id": "contact-1",
                    "source": "Clinic USSD",
                    "timestamp": "2025-02-11 10:17",
                },
                {
                    "contact_id": "contact-2",
                    "source": "WhatsApp",
                    "timestamp": "2025-02-11 10:18",
                },
            ]
        )

    create_registration_channel_file(
        None,
        input_path,
        output_filename=output_path,
        uuid_urn_lookup=lookup,
    )

    assert read_csv_rows(output_path) == [
        {"urn": "27820000001", "reg_channel": "ussd"},
        {"urn": "27820000002", "reg_channel": "whatsapp"},
    ]
