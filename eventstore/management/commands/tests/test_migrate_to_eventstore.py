from datetime import date
from uuid import UUID

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from changes.models import Change
from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    IdentificationSwitch,
    LanguageSwitch,
    MSISDNSwitch,
    OptOut,
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

    def test_babyswitch_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="baby_switch",
            source=source,
            validated=True,
        )

        call_command("migrate_to_eventstore")

        [change] = BabySwitch.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")

    def test_optout_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="momconnect_nonloss_optout",
            source=source,
            validated=True,
            data={
                "identity_store_optout": {"optout_type": "forget"},
                "reason": "babyloss",
            },
        )

        call_command("migrate_to_eventstore")

        [change] = OptOut.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.optout_type, "forget")
        self.assertEqual(change.reason, "babyloss")
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")

    def test_channelswitch_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="switch_channel",
            source=source,
            validated=True,
            data={"channel": "whatsapp"},
        )

        call_command("migrate_to_eventstore")

        [change] = ChannelSwitch.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.from_channel, "SMS")
        self.assertEqual(change.to_channel, "WhatsApp")
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")

    def test_msisdnswitch_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="momconnect_change_msisdn",
            source=source,
            validated=True,
            data={"msisdn": "+27820001001"},
        )

        call_command("migrate_to_eventstore")

        [change] = MSISDNSwitch.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.new_msisdn, "+27820001001")
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")

    def test_languageswitch_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="momconnect_change_language",
            source=source,
            validated=True,
            data={"language": "afr_ZA", "old_language": "zul_ZA"},
        )

        call_command("migrate_to_eventstore")

        [change] = LanguageSwitch.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.old_language, "zul")
        self.assertEqual(change.new_language, "afr")
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")

    def test_identificationswitch_change(self):
        user = User.objects.create_user("testusername")
        source = Source.objects.create(
            name="testsource", authority="patient", user=user
        )
        Change.objects.create(
            id="7fd2b2d4-e5fd-4264-b365-d2eda1764ba4",
            registrant_id="0bbb7161-ba0a-45e2-9888-d1a29fa01b40",
            action="momconnect_change_identification",
            source=source,
            validated=True,
            data={
                "id_type": "passport",
                "passport_origin": "bw",
                "passport_no": "A123456",
            },
        )

        call_command("migrate_to_eventstore")

        [change] = IdentificationSwitch.objects.all()
        self.assertEqual(change.id, UUID("7fd2b2d4-e5fd-4264-b365-d2eda1764ba4"))
        self.assertEqual(
            change.contact_id, UUID("0bbb7161-ba0a-45e2-9888-d1a29fa01b40")
        )
        self.assertEqual(change.new_identification_type, "passport")
        self.assertEqual(change.new_passport_country, "bw")
        self.assertEqual(change.new_passport_number, "A123456")
        self.assertEqual(change.source, "testsource")
        self.assertEqual(change.created_by, "testusername")
