from datetime import date
from uuid import UUID

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from eventstore.models import (
    CHWRegistration,
    PMTCTRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from registrations.models import Registration, Source


class MigrateToEventstoreTests(TestCase):
    def test_public_registration(self):
        """
        Should successfully migrate a public registration
        """
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Registration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            reg_type="whatsapp_prebirth",
            source=source,
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            data={
                "operator_id": "21fad17c-49c3-4315-b269-c5eaf6026b0d",
                "language": "eng_ZA",
            },
            validated=True,
        )

        call_command("migrate_to_eventstore")

        [new_reg] = PublicRegistration.objects.all()
        self.assertEqual(new_reg.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            new_reg.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(
            new_reg.device_contact_id, UUID("21fad17c-49c3-4315-b269-c5eaf6026b0d")
        )
        self.assertEqual(new_reg.source, "testsource")
        self.assertEqual(new_reg.language, "eng")
        self.assertEqual(new_reg.channel, "WhatsApp")
        self.assertEqual(new_reg.created_by, "testusername")

    def test_chw_registration(self):
        """
        Should successfully migrate a public registration
        """
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="hw_partial", user=user
        )
        Registration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            reg_type="whatsapp_prebirth",
            source=source,
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            data={
                "operator_id": "21fad17c-49c3-4315-b269-c5eaf6026b0d",
                "language": "eng_ZA",
                "id_type": "none",
                "mom_dob": "1990-01-01",
            },
            validated=True,
        )

        call_command("migrate_to_eventstore")

        [new_reg] = CHWRegistration.objects.all()
        self.assertEqual(new_reg.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            new_reg.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(
            new_reg.device_contact_id, UUID("21fad17c-49c3-4315-b269-c5eaf6026b0d")
        )
        self.assertEqual(new_reg.source, "testsource")
        self.assertEqual(new_reg.language, "eng")
        self.assertEqual(new_reg.id_type, "dob")
        self.assertEqual(new_reg.date_of_birth, date(1990, 1, 1))
        self.assertEqual(new_reg.channel, "WhatsApp")
        self.assertEqual(new_reg.created_by, "testusername")

    def test_prebirth_registration(self):
        """
        Should successfully migrate a public registration
        """
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="hw_full", user=user
        )
        Registration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            reg_type="whatsapp_prebirth",
            source=source,
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            data={
                "operator_id": "21fad17c-49c3-4315-b269-c5eaf6026b0d",
                "language": "eng_ZA",
                "id_type": "none",
                "mom_dob": "1990-01-01",
                "edd": "2020-01-01",
                "faccode": "123456",
            },
            validated=True,
        )

        call_command("migrate_to_eventstore")

        [new_reg] = PrebirthRegistration.objects.all()
        self.assertEqual(new_reg.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            new_reg.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(
            new_reg.device_contact_id, UUID("21fad17c-49c3-4315-b269-c5eaf6026b0d")
        )
        self.assertEqual(new_reg.id_type, "dob")
        self.assertEqual(new_reg.date_of_birth, date(1990, 1, 1))
        self.assertEqual(new_reg.channel, "WhatsApp")
        self.assertEqual(new_reg.language, "eng")
        self.assertEqual(new_reg.edd, date(2020, 1, 1))
        self.assertEqual(new_reg.facility_code, "123456")
        self.assertEqual(new_reg.source, "testsource")
        self.assertEqual(new_reg.created_by, "testusername")

    def test_pmtct_registration(self):
        """
        Should successfully migrate a public registration
        """
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Registration.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            reg_type="pmtct_prebirth",
            source=source,
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            data={
                "operator_id": "21fad17c-49c3-4315-b269-c5eaf6026b0d",
                "mom_dob": "1990-01-01",
            },
            validated=True,
        )

        call_command("migrate_to_eventstore")

        [new_reg] = PMTCTRegistration.objects.all()
        self.assertEqual(new_reg.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            new_reg.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(
            new_reg.device_contact_id, UUID("21fad17c-49c3-4315-b269-c5eaf6026b0d")
        )
        self.assertEqual(new_reg.source, "testsource")
        self.assertEqual(new_reg.date_of_birth, date(1990, 1, 1))
        self.assertEqual(new_reg.created_by, "testusername")
