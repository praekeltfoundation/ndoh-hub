import responses
from django.core.management import call_command
from django.test import TestCase
from temba_client.v2 import TembaClient

from eventstore.management.commands import migrate_registration_info
from eventstore.models import (
    CHWRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)


class MigrateToEventstoreTests(TestCase):
    @responses.activate
    def test_add_channel_public_registration(self):
        """
        Should successfully migrate a public registration
        """
        p = PublicRegistration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            device_contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            language="zul",
            channel="",
        )
        migrate_registration_info.rapidpro = TembaClient("textit.in", "test-token")
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=0bbb7161-ba0a-45e2-9888-d1a29fa01b40",  # noqa
            json={
                "results": [
                    {
                        "uuid": "0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"facility_code": "123456", "channel": "SMS"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        call_command("migrate_registration_info")

        p.refresh_from_db()
        self.assertEqual(p.channel, "SMS")

    @responses.activate
    def test_add_channel_prebirth_registration(self):
        """
        Should successfully migrate a prebirth registration
        """
        p = PrebirthRegistration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            device_contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            edd="2020-12-12",
            language="zul",
            channel="",
        )
        migrate_registration_info.rapidpro = TembaClient("textit.in", "test-token")
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=0bbb7161-ba0a-45e2-9888-d1a29fa01b40",  # noqa
            json={
                "results": [
                    {
                        "uuid": "0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"facility_code": "123456", "channel": "SMS"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        call_command("migrate_registration_info")

        p.refresh_from_db()
        self.assertEqual(p.channel, "SMS")

    @responses.activate
    def test_add_channel_postbirth_registration(self):
        """
        Should successfully migrate a public registration
        """
        p = PostbirthRegistration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            device_contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            baby_dob="2020-12-12",
            language="zul",
            channel="",
        )
        migrate_registration_info.rapidpro = TembaClient("textit.in", "test-token")
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=0bbb7161-ba0a-45e2-9888-d1a29fa01b40",  # noqa
            json={
                "results": [
                    {
                        "uuid": "0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
                        "name": "",
                        "language": "zul",
                        "groups": [],
                        "fields": {"facility_code": "123456", "channel": "SMS"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        call_command("migrate_registration_info")

        p.refresh_from_db()
        self.assertEqual(p.channel, "SMS")

    @responses.activate
    def test_add_channel_chw_registration(self):
        """
        Should successfully migrate a public registration
        """
        p = CHWRegistration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            device_contact_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            language="eng",
            channel="",
        )
        migrate_registration_info.rapidpro = TembaClient("textit.in", "test-token")
        responses.add(
            responses.GET,
            "https://textit.in/api/v2/contacts.json?uuid=0bbb7161-ba0a-45e2-9888-d1a29fa01b40",  # noqa
            json={
                "results": [
                    {
                        "uuid": "0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
                        "name": "",
                        "language": "eng",
                        "groups": [],
                        "fields": {"facility_code": "123456", "channel": "SMS"},
                        "blocked": False,
                        "stopped": False,
                        "created_on": "2015-11-11T08:30:24.922024+00:00",
                        "modified_on": "2015-11-11T08:30:25.525936+00:00",
                        "urns": ["tel:+27820001001"],
                    }
                ],
                "next": None,
            },
        )

        call_command("migrate_registration_info")

        p.refresh_from_db()
        self.assertEqual(p.channel, "SMS")
