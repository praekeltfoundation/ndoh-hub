from unittest import TestCase

from .upload_to_rapidpro import fields_from_contact


class FieldsFromContactTests(TestCase):
    def test_no_fields(self):
        """
        Should skip adding the fields if they don't exist on the contact
        """
        self.assertEqual(fields_from_contact({}, {}), {})

    def test_field_values(self):
        """
        Should all all the available fields with their correct values
        """
        self.maxDiff = None
        self.assertEqual(
            fields_from_contact(
                {
                    k: f"{k.replace('_', '-')}-uuid"
                    for k in [
                        "consent",
                        "baby_dob1",
                        "baby_dob2",
                        "baby_dob3",
                        "date_of_birth",
                        "edd",
                        "facility_code",
                        "identification_type",
                        "id_number",
                        "optout_reason",
                        "optout_timestamp",
                        "passport_number",
                        "passport_origin",
                        "pmtct_risk",
                        "preferred_channel",
                        "public_registration_date",
                        "registered_by",
                    ]
                },
                {
                    "consent": True,
                    "baby_dobs": [
                        "2020-01-01",
                        "2020-01-01T00:00:00Z",
                        "2019-01-01",
                        "2018-01-01T00:00:00Z",
                        "2017-01-01",
                    ],
                    "mom_dob": "1990-01-01",
                    "edd": "2021-01-01",
                    "faccode": "123456",
                    "id_type": "none",
                    "sa_id_no": "9001010000088",
                    "optout_reason": "babyloss",
                    "optout_timestamp": "2020-02-02",
                    "passport_no": "A12345",
                    "passport_origin": "zw",
                    "pmtct_risk": "normal",
                    "channel": "WhatsApp",
                    "public_registration_date": "2019-02-02",
                    "msisdn_device": "+27820001002",
                },
            ),
            {
                "consent-uuid": {"text": "TRUE"},
                "baby-dob1-uuid": {
                    "datetime": "2020-01-01T00:00:00+00:00",
                    "text": "2020-01-01T00:00:00+00:00",
                },
                "baby-dob2-uuid": {
                    "datetime": "2019-01-01T00:00:00+00:00",
                    "text": "2019-01-01T00:00:00+00:00",
                },
                "baby-dob3-uuid": {
                    "datetime": "2018-01-01T00:00:00+00:00",
                    "text": "2018-01-01T00:00:00+00:00",
                },
                "date-of-birth-uuid": {
                    "datetime": "1990-01-01T00:00:00+00:00",
                    "text": "1990-01-01T00:00:00+00:00",
                },
                "edd-uuid": {
                    "datetime": "2021-01-01T00:00:00+00:00",
                    "text": "2021-01-01T00:00:00+00:00",
                },
                "facility-code-uuid": {"text": "123456"},
                "identification-type-uuid": {"text": "dob"},
                "id-number-uuid": {"text": "9001010000088"},
                "optout-reason-uuid": {"text": "babyloss"},
                "optout-timestamp-uuid": {
                    "datetime": "2020-02-02T00:00:00+00:00",
                    "text": "2020-02-02T00:00:00+00:00",
                },
                "passport-number-uuid": {"text": "A12345"},
                "passport-origin-uuid": {"text": "zw"},
                "pmtct-risk-uuid": {"text": "normal"},
                "preferred-channel-uuid": {"text": "WhatsApp"},
                "public-registration-date-uuid": {
                    "datetime": "2019-02-02T00:00:00+00:00",
                    "text": "2019-02-02T00:00:00+00:00",
                },
                "registered-by-uuid": {"text": "+27820001002"},
            },
        )
