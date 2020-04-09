from django.test import TestCase

from eventstore.models import CDUAddressUpdate
from eventstore.tasks import read_data, upload_and_delete_cdu_address_updates


class ProcessCDUExportTasks(TestCase):
    def test_upload_and_delete_cdu_address_updates(self):
        CDUAddressUpdate.objects.create(
            msisdn="+2349030000000",
            first_name="Jerry",
            last_name="Cooney",
            id_type="dob",
            id_number="12345",
            date_of_birth="1990-04-04",
            folder_number="1234567",
            district="Lagos",
            municipality="Lagos",
            city="Lagos",
            suburb="Lekki",
            street_name="Igbo Efun",
            street_number="10045",
        )

        CDUAddressUpdate.objects.create(
            msisdn="+2345555555555",
            first_name="John",
            last_name="Terry",
            id_type="dob",
            id_number="12123456",
            date_of_birth="1982-05-04",
            folder_number="2534567",
            district="Lagos",
            municipality="Lagos",
            city="Lagos",
            suburb="Lekki",
            street_name="Igbo Efun",
            street_number="10067",
        )

        upload_and_delete_cdu_address_updates(self)

    def setUp(self):
        self.data = "./CDU_address.csv"

    def test_csv_read_data_header(self):
        self.assertEqual(
            read_data(self.data)[0],
            [
                "msisdn",
                "first_name",
                "last_name",
                "id_type",
                "id_number",
                "date_of_birth",
                "folder_number",
                "district",
                "municipality",
                "city",
                "suburb",
                "street_name",
                "street_number",
            ],
        )

    def test_csv_read_data_rows(self):
        self.assertEqual(
            read_data(self.data)[1],
            [
                "+2349030000000",
                "Jerry",
                "Cooney",
                "dob",
                "12345",
                "1990-04-04",
                "1234567",
                "Lagos",
                "Lagos",
                "Lagos",
                "Lekki",
                "Igbo Efun",
                "10045",
            ],
        )
        self.assertEqual(
            read_data(self.data)[2],
            [
                "+2345555555555",
                "John",
                "Terry",
                "dob",
                "12123456",
                "1982-05-04",
                "2534567",
                "Lagos",
                "Lagos",
                "Lagos",
                "Lekki",
                "Igbo Efun",
                "10067",
            ],
        )
