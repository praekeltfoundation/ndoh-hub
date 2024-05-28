from django.core.management import call_command
from django.test import TestCase

from registrations.models import ClinicCode


class UpdateClinicsTestCase(TestCase):
    def test_update_clinics(self):
        existing_clinic = ClinicCode.objects.create(
            uid="rICptExz4NW", code="110533", value="110533"
        )

        call_command(
            "update_clinics",
            "./registrations/management/commands/tests/test_clinic_list.csv",
        )

        existing_clinic.refresh_from_db()
        self.assertEqual(existing_clinic.name, "Test Clinic 1")
        self.assertEqual(existing_clinic.location, "-33.54222+025.69077/")
        self.assertEqual(existing_clinic.province, "ZA-EC")
        self.assertEqual(existing_clinic.area_type, "Urban")
        self.assertEqual(existing_clinic.unit_type, "Clinic")
        self.assertEqual(existing_clinic.district, "Sarah Baartman DM")
        self.assertEqual(existing_clinic.municipality, "Sundays River Valley LM")

        new_clinic = ClinicCode.objects.get(uid="QYdJjvibz4e")
        self.assertEqual(new_clinic.name, "Test Clinic 2")
        self.assertEqual(new_clinic.location, "-32.69994+026.29404/")
        self.assertEqual(new_clinic.province, "ZA-EC")
        self.assertEqual(new_clinic.area_type, "Urban")
        self.assertEqual(new_clinic.unit_type, "Clinic")
        self.assertEqual(new_clinic.district, "Amathole DM")
        self.assertEqual(new_clinic.municipality, "Raymond Mhlaba LM")

        self.assertEqual(ClinicCode.objects.count(), 2)
