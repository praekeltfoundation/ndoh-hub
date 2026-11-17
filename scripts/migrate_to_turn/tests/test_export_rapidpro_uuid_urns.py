import csv
from types import SimpleNamespace

import pytest
from temba_client.exceptions import TembaConnectionError

from scripts.migrate_to_turn.export_rapidpro_uuid_urns import (
    export_rapidpro_uuid_urns,
    iter_contact_batches,
)


def read_csv_rows(path):
    with path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


class FakeContactsQuery:
    def __init__(self, batches):
        self.batches = batches

    def iterfetches(self, retry_on_rate_exceed=True, resume_cursor=None):
        return FakeBatchIterator(self.batches, resume_cursor=resume_cursor)


class FakeBatchIterator:
    def __init__(self, batches, resume_cursor=None):
        self.batches = batches
        self.index = resume_cursor or 0
        self.cursor = resume_cursor

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.batches):
            raise StopIteration()

        batch = self.batches[self.index]
        self.index += 1
        self.cursor = self.index
        return batch

    def get_cursor(self):
        return self.cursor


class FakeClient:
    def __init__(self, batches):
        self.batches = batches

    def get_contacts(self):
        return FakeContactsQuery(self.batches)


class FakeIterator:
    def __init__(self, client, resume_cursor=None):
        self.client = client
        self.index = resume_cursor or 0
        self.cursor = resume_cursor

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.client.batches):
            raise StopIteration()

        if self.client.fail_once_cursor == self.index and self.index not in self.client.failed:
            self.client.failed.add(self.index)
            raise TembaConnectionError()

        event = self.client.batches[self.index]
        self.index += 1
        self.cursor = self.index
        return event

    def get_cursor(self):
        return self.cursor


class RetryClient:
    def __init__(self, batches, fail_once_cursor=None):
        self.batches = batches
        self.fail_once_cursor = fail_once_cursor
        self.failed = set()

    def get_contacts(self):
        return self

    def iterfetches(self, retry_on_rate_exceed=True, resume_cursor=None):
        return FakeIterator(self, resume_cursor=resume_cursor)


def test_export_rapidpro_uuid_urns_writes_uuid_and_whatsapp_urns(tmp_path):
    output_path = tmp_path / "rapidpro_uuid_urns.csv"
    client = FakeClient(
        [
            [
                SimpleNamespace(uuid="contact-1", urns=["whatsapp:27820000001"]),
                SimpleNamespace(uuid="contact-2", urns=["tel:+27123"]),
            ],
            [
                SimpleNamespace(
                    uuid="contact-3",
                    urns=["tel:+27124", "whatsapp:27820000003"],
                )
            ],
        ]
    )

    export_rapidpro_uuid_urns(client, output_filename=output_path)

    assert read_csv_rows(output_path) == [
        {"contact_id": "contact-1", "urn": "27820000001"},
        {"contact_id": "contact-3", "urn": "27820000003"},
    ]


def test_iter_contact_batches_retries_with_resume_cursor(monkeypatch):
    batches = [
        [SimpleNamespace(uuid="contact-1", urns=["whatsapp:27820000001"])],
        [SimpleNamespace(uuid="contact-2", urns=["whatsapp:27820000002"])],
    ]

    monkeypatch.setattr(
        "scripts.migrate_to_turn.export_rapidpro_uuid_urns.time.sleep",
        lambda _: None,
    )

    batches = list(
        iter_contact_batches(
            RetryClient(batches, fail_once_cursor=1),
            max_retries=2,
            backoff_seconds=1,
        )
    )

    assert [batch[0].uuid for batch in batches] == ["contact-1", "contact-2"]


def test_iter_contact_batches_raises_after_retry_limit(monkeypatch):
    monkeypatch.setattr(
        "scripts.migrate_to_turn.export_rapidpro_uuid_urns.time.sleep",
        lambda _: None,
    )

    with pytest.raises(TembaConnectionError):
        list(
            iter_contact_batches(
                RetryClient(
                    [[SimpleNamespace(uuid="contact-1", urns=["whatsapp:27820000001"])]],
                    fail_once_cursor=0,
                ),
                max_retries=0,
                backoff_seconds=1,
            )
        )
