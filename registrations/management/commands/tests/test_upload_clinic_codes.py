import tempfile
from csv import DictWriter

from django.core.management import call_command
from django.test import TestCase

from registrations.models import ClinicCode


class UploadClinicCodesTests(TestCase):
    def test_successful_upload(self):
        with tempfile.NamedTemporaryFile("w") as f:
            writer = DictWriter(f, ["uid", "code", "facility", "province", "location"])
            writer.writeheader()
            writer.writerow(
                {
                    "uid": "abc123",
                    "code": "123456",
                    "facility": "Test facility",
                    "province": "wc Western Cape",
                    "location": "[12.34,-34.21]",
                }
            )
            f.seek(0)
            call_command("upload_clinic_codes", f.name)
        [cliniccode] = ClinicCode.objects.all()
        self.assertEqual(cliniccode.uid, "abc123")
        self.assertEqual(cliniccode.code, "123456")
        self.assertEqual(cliniccode.value, "123456")
        self.assertEqual(cliniccode.name, "Test facility")
        self.assertEqual(cliniccode.province, "ZA-WC")
        self.assertEqual(cliniccode.location, "-34.21+012.34/")
