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
        self.assertEqual(existing_clinic.area_type, "Urban")
        self.assertEqual(existing_clinic.unit_type, "Clinic")
        self.assertEqual(existing_clinic.district, "Sarah Baartman DM")
        self.assertEqual(existing_clinic.municipality, "Sundays River Valley LM")

        new_clinic = ClinicCode.objects.filter(uid="QYdJjvibz4e").first()
        self.assertIsNone(new_clinic)

        self.assertEqual(ClinicCode.objects.count(), 1)
