import datetime
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.serializers import ValidationError

from registrations.models import Registration, Source
from registrations.serializers import (
    JembiAppRegistrationSerializer,
    MSISDNField,
    RapidProClinicRegistrationSerializer,
)


def override_get_today():
    return datetime.date(2016, 1, 1)


class MSISDNFieldTests(TestCase):
    def test_internal_value(self):
        """
        A phone number sent to the field should be formatted in E164 format
        """
        field = MSISDNField(country="ZA")
        self.assertEqual(field.run_validation("0821234567"), "+27821234567")

    def test_bad_input(self):
        """
        If the input cannot be parsed, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            "The string supplied did not seem to be a phone number",
            field.run_validation,
            "1",
        )

    def test_impossible_phone_number(self):
        """
        If a phone number is not possible, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            "Not a possible phone number",
            field.run_validation,
            "+120012301",
        )

    def test_invalid_phone_number(self):
        """
        If a phone number is not valid, a validation error should be raised
        """
        field = MSISDNField()
        self.assertRaisesMessage(
            ValidationError,
            "Not a valid phone number",
            field.run_validation,
            "+12001230101",
        )

    def test_representation(self):
        """
        The representation should be in E164
        """
        field = MSISDNField(country="ZA")
        self.assertEqual(field.to_representation("0821234567"), "+27821234567")


class JembiAppRegistrationSerializerTests(TestCase):
    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_valid_registration(self):
        """
        If the registration is valid, then the serializer should be valid
        """
        self.maxDiff = None
        data = {
            "mom_msisdn": "0820000001",
            "hcw_msisdn": "0820000002",
            "mom_id_type": "sa_id",
            "mom_sa_id_no": "8606045069081",
            "mom_dob": "1988-01-01",
            "mom_lang": "eng_ZA",
            "mom_edd": "2016-06-06",
            "mom_consent": True,
            "clinic_code": "123456",
            "mha": 1,
            "created": "2016-01-01 00:00:00",
        }
        serializer = JembiAppRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            dict(serializer.validated_data),
            {
                "external_id": None,
                "msisdn_registrant": "+27820000001",
                "msisdn_device": "+27820000002",
                "id_type": "sa_id",
                "sa_id_no": "8606045069081",
                "mom_dob": datetime.date(1988, 1, 1),
                "language": "eng_ZA",
                "edd": datetime.date(2016, 6, 6),
                "consent": True,
                "faccode": "123456",
                "mha": 1,
                "created": datetime.datetime(2016, 1, 1, 0, 0, 0, 0, timezone.utc),
                "mom_whatsapp": False,
                "mom_pmtct": False,
                "mom_opt_in": False,
            },
        )

    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_missing_sa_id_no(self):
        """
        If the ID type is SA ID, then the SA ID number must be present
        """
        data = {
            "mom_msisdn": "0820000001",
            "hcw_msisdn": "0820000002",
            "mom_id_type": "sa_id",
            "mom_dob": "1988-01-01",
            "mom_lang": "eng_ZA",
            "mom_edd": "2016-06-06",
            "mom_consent": True,
            "clinic_code": "123456",
            "mha": 1,
            "swt": 2,
            "created": "2016-01-01 00:00:00",
        }
        serializer = JembiAppRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "non_field_errors": [
                    "mom_sa_id_no field must be supplied if mom_id_type is sa_id"
                ]
            },
        )

    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_missing_passport_no(self):
        """
        If the ID type is passport, then the passport number must be present
        """
        data = {
            "mom_msisdn": "0820000001",
            "hcw_msisdn": "0820000002",
            "mom_id_type": "passport",
            "mom_passport_origin": "na",
            "mom_dob": "1988-01-01",
            "mom_lang": "eng_ZA",
            "mom_edd": "2016-06-06",
            "mom_consent": True,
            "clinic_code": "123456",
            "mha": 1,
            "swt": 2,
            "created": "2016-01-01 00:00:00",
        }
        serializer = JembiAppRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "non_field_errors": [
                    "mom_passport_no field must be supplied if mom_id_type is "
                    "passport"
                ]
            },
        )

    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_missing_passport_origin(self):
        """
        If the ID type is passport, then the passport origin must be present
        """
        data = {
            "mom_msisdn": "0820000001",
            "hcw_msisdn": "0820000002",
            "mom_id_type": "passport",
            "mom_passport_no": "12345",
            "mom_dob": "1988-01-01",
            "mom_lang": "eng_ZA",
            "mom_edd": "2016-06-06",
            "mom_consent": True,
            "clinic_code": "123456",
            "mha": 1,
            "swt": 2,
            "created": "2016-01-01 00:00:00",
        }
        serializer = JembiAppRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors,
            {
                "non_field_errors": [
                    "mom_passport_origin field must be supplied if mom_id_type is "
                    "passport"
                ]
            },
        )

    @mock.patch("ndoh_hub.utils.get_today", override_get_today)
    def test_duplicate_external_id(self):
        """
        If a registration with the given external_id already exists, then it
        should be considered duplicate, and not allowed to be created
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        Registration.objects.create(source=source, external_id="test-external-id")
        data = {
            "external_id": "test-external-id",
            "mom_edd": "2016-06-06",
            "mom_msisdn": "+27820000000",
            "mom_consent": True,
            "created": "2016-01-01 00:00:00",
            "hcw_msisdn": "+27821111111",
            "clinic_code": "123456",
            "mom_lang": "eng_ZA",
            "mha": 1,
            "mom_dob": "1988-01-01",
            "mom_id_type": "none",
        }
        serializer = JembiAppRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors, {"external_id": ["This field must be unique."]}
        )


@mock.patch("ndoh_hub.utils.get_today", override_get_today)
class RapidProClinicRegistrationSerializerTests(TestCase):
    VALID_REGISTRATION = {
        "mom_msisdn": "0820000001",
        "device_msisdn": "0820000002",
        "mom_id_type": "sa_id",
        "mom_sa_id_no": "8606045069081",
        "mom_lang": "eng_ZA",
        "registration_type": "prebirth",
        "mom_edd": "2016-06-06",
        "clinic_code": "123456",
        "channel": "WhatsApp",
        "created": "2016-01-01 00:00:00",
    }

    def test_valid_registration(self):
        """
        If the registration is valid, then the serializer should be valid
        """
        serializer = RapidProClinicRegistrationSerializer(data=self.VALID_REGISTRATION)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            dict(serializer.validated_data),
            {
                "mom_msisdn": "+27820000001",
                "device_msisdn": "+27820000002",
                "mom_id_type": "sa_id",
                "mom_sa_id_no": "8606045069081",
                "mom_lang": "eng_ZA",
                "registration_type": "prebirth",
                "mom_edd": datetime.date(2016, 6, 6),
                "clinic_code": "123456",
                "channel": "WhatsApp",
                "created": datetime.datetime(2016, 1, 1, 0, 0, 0, 0, timezone.utc),
            },
        )

    def test_sa_id_required(self):
        """
        If the id type is sa_id, then the mom_sa_id_no field must be populated.
        """
        data = self.VALID_REGISTRATION.copy()
        data["mom_id_type"] = "sa_id"
        data["mom_sa_id_no"] = None
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mom_sa_id_no", str(serializer.errors))

    def test_passport_required(self):
        """
        If the id type is passport, then the passport ID and number fields must be
        populated
        """
        data = self.VALID_REGISTRATION.copy()

        data["mom_id_type"] = "passport"
        data["mom_passport_no"] = None
        data["mom_passport_origin"] = "na"
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mom_passport_no", str(serializer.errors))

        data["mom_passport_no"] = "123456"
        data["mom_passport_origin"] = None
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mom_passport_origin", str(serializer.errors))

    def test_no_id_required(self):
        """
        If the id type is none, then the date of birth must be populated
        """
        data = self.VALID_REGISTRATION.copy()
        data["mom_id_type"] = "none"
        data["mom_dob"] = None
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mom_dob", str(serializer.errors))

    def test_prebirth_required(self):
        """
        If the registration type is prebirth, then the EDD must be supplied
        """
        data = self.VALID_REGISTRATION.copy()
        data["registration_type"] = "prebirth"
        data["mom_edd"] = None
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mom_edd", str(serializer.errors))

    def test_postbirth_required(self):
        """
        If the registration type is postbirth, then the baby dob must be supplied
        """
        data = self.VALID_REGISTRATION.copy()
        data["registration_type"] = "postbirth"
        data["baby_dob"] = None
        serializer = RapidProClinicRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("baby_dob", str(serializer.errors))
