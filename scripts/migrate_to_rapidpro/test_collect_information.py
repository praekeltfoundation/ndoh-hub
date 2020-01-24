from collections import OrderedDict
import datetime
from unittest import TestCase
from .collect_information import (
    get_addresses,
    process_identity,
    process_optout,
    process_registration,
    process_change,
    process_subscription,
    deduplicate_msisdns,
)


class GetAddressesTests(TestCase):
    def test_ignore_invalid_numbers(self):
        """
        Ignores invalid numbers
        """
        self.assertEqual(get_addresses({"msisdn": {"abc": {}, "123": {}}}), [])

    def test_normalises_numbers(self):
        """
        If a number is not in E164 format, it should be converted
        """
        self.assertEqual(
            get_addresses({"msisdn": {"0820001001": {}}}), ["+27820001001"]
        )

    def test_default(self):
        """
        If one of the addresses is default, only that address should be returned
        """
        self.assertEqual(
            get_addresses(
                {
                    "msisdn": {
                        "+27820001001": {},
                        "+27820001002": {"default": True},
                        "+27820001003": {},
                    }
                }
            ),
            ["+27820001002"],
        )

    def test_optout(self):
        """
        If an address is opted out, it shouldn't be returned
        """
        self.assertEqual(
            get_addresses(
                {"msisdn": {"+27820001001": {"optedout": True}, "+27820001002": {}}}
            ),
            ["+27820001002"],
        )

    def test_multiple(self):
        """
        If there are multiple valid addresses, they should all be returned
        """
        self.assertEqual(
            get_addresses({"msisdn": {"+27820001001": {}, "+27820001002": {}}}),
            ["+27820001001", "+27820001002"],
        )


class ProcessIdentityTests(TestCase):
    def test_all_identity_details_stored(self):
        """
        All the relevant details on the identity should be stored in the dictionary
        """
        identities = {}
        process_identity(
            identities,
            "identity-uuid",
            {
                "addresses": {"msisdn": {"+27820001001": {}}},
                "operator_id": "operator_uuid",
                "passport_no": "A12345",
                "passport_origin": "zw",
                "consent": True,
                "sa_id_no": "123456",
                "mom_given_name": "Test name",
                "mom_family_name": "Test family name",
                "faccode": "123456",
                "id_type": "sa_id",
                "lang_code": "zul_ZA",
                "pmtct": {"risk_status": "high"},
                "mom_dob": "1990-01-01",
            },
            2,
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "msisdns": ["+27820001001"],
                    "operator_id": "operator_uuid",
                    "passport_no": "A12345",
                    "passport_origin": "zw",
                    "consent": True,
                    "sa_id_no": "123456",
                    "mom_given_name": "Test name",
                    "mom_family_name": "Test family name",
                    "faccode": "123456",
                    "id_type": "sa_id",
                    "language": "zul",
                    "pmtct_risk": "high",
                    "mom_dob": "1990-01-01",
                    "uuid": "identity-uuid",
                    "failed_msgs_count": 2,
                }
            },
        )

    def test_no_fields(self):
        """
        It should handle missing fields
        """
        identities = {}
        process_identity(
            identities,
            "identity-uuid",
            {"addresses": {"msisdn": {"+27820001001": {}}}},
            2,
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "msisdns": ["+27820001001"],
                    "uuid": "identity-uuid",
                    "failed_msgs_count": 2,
                }
            },
        )


class ProcessOptOutTests(TestCase):
    def test_optout_added(self):
        """
        Adds the optout to the identity if there is none
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}
        process_optout(
            identities, "identity-uuid", datetime.datetime(2020, 1, 1), "babyloss"
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "optout_timestamp": "2020-01-01T00:00:00",
                    "optout_reason": "babyloss",
                }
            },
        )

    def test_replace_optout(self):
        """
        If this optout is newer than the one on the identity, it should be replaced
        """
        identities = {
            "identity-uuid": {
                "uuid": "identity-uuid",
                "optout_timestamp": "2020-01-01T00:00:00",
            }
        }
        process_optout(
            identities, "identity-uuid", datetime.datetime(2020, 1, 2), "babyloss"
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "optout_timestamp": "2020-01-02T00:00:00",
                    "optout_reason": "babyloss",
                }
            },
        )

    def test_skip_optout(self):
        """
        If this optout is older than the one on the identity, it shouldn't be replaced
        """
        identities = {
            "identity-uuid": {
                "uuid": "identity-uuid",
                "optout_timestamp": "2020-01-02T00:00:00",
            }
        }
        process_optout(
            identities, "identity-uuid", datetime.datetime(2020, 1, 1), "babyloss"
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "optout_timestamp": "2020-01-02T00:00:00",
                }
            },
        )


class ProcessRegistrationTests(TestCase):
    def test_all_fields(self):
        """
        It should extract the relevant fields from the registration onto the identity
        """
        identities = {
            "identity-uuid": {"uuid": "identity-uuid", "msisdns": ["+27820001001"]}
        }
        process_registration(
            identities,
            "identity-uuid",
            {
                "edd": "2020-01-01",
                "faccode": "12345",
                "id_type": "sa_id",
                "mom_dob": "1990-01-01",
                "mom_given_name": "test name",
                "mom_family_name": "test family name",
                "uuid_device": "identity-uuid",
                "passport_no": "A12345",
                "passport_origin": "zw",
                "sa_id_no": "123456",
                "consent": True,
                "baby_dob": "2020-01-02",
                "language": "zul_ZA",
            },
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "msisdns": ["+27820001001"],
                    "edd": "2020-01-01",
                    "faccode": "12345",
                    "id_type": "sa_id",
                    "mom_dob": "1990-01-01",
                    "mom_given_name": "test name",
                    "mom_family_name": "test family name",
                    "passport_no": "A12345",
                    "passport_origin": "zw",
                    "sa_id_no": "123456",
                    "consent": True,
                    "baby_dobs": ["2020-01-02"],
                    "language": "zul",
                    "msisdn_device": "+27820001001",
                }
            },
        )

    def test_no_overwrite(self):
        """
        Should not overwrite existing fields
        """
        identities = {
            "identity-uuid": {
                "uuid": "identity-uuid",
                "msisdns": ["+27820001001"],
                "edd": "2020-01-01",
                "faccode": "12345",
                "id_type": "sa_id",
                "mom_dob": "1990-01-01",
                "mom_given_name": "test name",
                "mom_family_name": "test family name",
                "msisdn_device": "+27820001002",
                "passport_no": "A12345",
                "passport_origin": "zw",
                "sa_id_no": "123456",
                "consent": True,
                "baby_dobs": ["2020-01-02"],
                "language": "zul",
            }
        }
        process_registration(
            identities,
            "identity-uuid",
            {
                "edd": "2020-01-02",
                "faccode": "12346",
                "id_type": "passport",
                "mom_dob": "1990-01-02",
                "mom_given_name": "test name2",
                "mom_family_name": "test family name2",
                "uuid_device": "identity-uuid",
                "passport_no": "A12346",
                "passport_origin": "mw",
                "sa_id_no": "123457",
                "consent": False,
                "baby_dob": "2020-01-04",
                "language": "xho_ZA",
            },
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "msisdns": ["+27820001001"],
                    "edd": "2020-01-01",
                    "faccode": "12345",
                    "id_type": "sa_id",
                    "mom_dob": "1990-01-01",
                    "mom_given_name": "test name",
                    "mom_family_name": "test family name",
                    "passport_no": "A12345",
                    "passport_origin": "zw",
                    "sa_id_no": "123456",
                    "consent": True,
                    "baby_dobs": ["2020-01-02", "2020-01-04"],
                    "language": "zul",
                    "msisdn_device": "+27820001002",
                }
            },
        )

    def test_no_fields(self):
        """
        Should handle missing fields
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}
        process_registration(identities, "identity-uuid", {})
        self.assertEqual(identities, {"identity-uuid": {"uuid": "identity-uuid"}})


class ProcessChangeTests(TestCase):
    def test_unknown_action(self):
        """
        We should skip processing changes that are not optout or baby_switch
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}
        process_change(
            identities,
            "identity-uuid",
            "unknown-action",
            {},
            datetime.datetime(2020, 1, 1),
        )
        self.assertEqual(identities, {"identity-uuid": {"uuid": "identity-uuid"}})

    def test_optout(self):
        """
        If there is no optout, one should be added
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}
        process_change(
            identities,
            "identity-uuid",
            "momconnect_nonloss_optout",
            {"reason": "unknown"},
            datetime.datetime(2020, 1, 1),
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "optout_timestamp": "2020-01-01T00:00:00",
                    "optout_reason": "unknown",
                }
            },
        )

    def test_optout_overwrite(self):
        """
        If the optout is newer, it should overwrite
        """
        identities = {"identity-uuid": {"optout_timestamp": "2019-01-01T00:00:00"}}
        process_change(
            identities,
            "identity-uuid",
            "momconnect_nonloss_optout",
            {},
            datetime.datetime(2020, 1, 1),
        )
        self.assertEqual(
            identities, {"identity-uuid": {"optout_timestamp": "2020-01-01T00:00:00"}}
        )

    def test_optout_no_overwrite(self):
        """
        If the optout is older, it should not overwrite
        """
        identities = {"identity-uuid": {"optout_timestamp": "2020-01-01T00:00:00"}}
        process_change(
            identities,
            "identity-uuid",
            "momconnect_nonloss_optout",
            {},
            datetime.datetime(2019, 1, 1),
        )
        self.assertEqual(
            identities, {"identity-uuid": {"optout_timestamp": "2020-01-01T00:00:00"}}
        )

    def test_babyswitch_create(self):
        """
        Should create the baby dob list if not exists
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}
        process_change(
            identities,
            "identity-uuid",
            "baby_switch",
            {},
            datetime.datetime(2019, 1, 1),
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "uuid": "identity-uuid",
                    "baby_dobs": ["2019-01-01T00:00:00"],
                }
            },
        )

    def test_babyswitch_add(self):
        """
        Should add to the baby dob list if exists
        """
        identities = {"identity-uuid": {"baby_dobs": ["2020-01-01T00:00:00"]}}
        process_change(
            identities,
            "identity-uuid",
            "baby_switch",
            {},
            datetime.datetime(2019, 1, 1),
        )
        self.assertEqual(
            identities,
            {
                "identity-uuid": {
                    "baby_dobs": ["2020-01-01T00:00:00", "2019-01-01T00:00:00"]
                }
            },
        )


class ProcessSubscriptionTests(TestCase):
    def test_channel_prefer_whatsapp(self):
        """
        Should set the channel, but never overwrite WhatsApp with SMS
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}

        process_subscription(identities, "identity-uuid", "momconnect")
        self.assertEqual(
            identities, {"identity-uuid": {"uuid": "identity-uuid", "channel": "SMS"}}
        )

        process_subscription(identities, "identity-uuid", "whatsapp_momconnect")
        self.assertEqual(
            identities,
            {"identity-uuid": {"uuid": "identity-uuid", "channel": "WhatsApp"}},
        )

        process_subscription(identities, "identity-uuid", "momconnect")
        self.assertEqual(
            identities,
            {"identity-uuid": {"uuid": "identity-uuid", "channel": "WhatsApp"}},
        )

    def test_subscription_types(self):
        """
        Should add to the subscription list depending on the name
        """
        identities = {"identity-uuid": {"uuid": "identity-uuid"}}

        process_subscription(identities, "identity-uuid", "pmtct_prebirth.hw_full.1")
        self.assertEqual(identities["identity-uuid"]["subscriptions"], ["PMTCT"])

        process_subscription(identities, "identity-uuid", "loss_miscarriage.patient.1")
        self.assertEqual(
            identities["identity-uuid"]["subscriptions"], ["PMTCT", "Loss"]
        )
        self.assertEqual(identities["identity-uuid"]["optout_reason"], "miscarriage")

        process_subscription(
            identities, "identity-uuid", "momconnect_prebirth.hw_partial.1"
        )
        self.assertEqual(
            identities["identity-uuid"]["subscriptions"], ["PMTCT", "Loss", "Public"]
        )

        process_subscription(
            identities, "identity-uuid", "momconnect_prebirth.hw_full.3"
        )
        self.assertEqual(
            identities["identity-uuid"]["subscriptions"],
            ["PMTCT", "Loss", "Public", "Prebirth 3"],
        )

        process_subscription(
            identities, "identity-uuid", "momconnect_postbirth.hw_full.2"
        )
        self.assertEqual(
            identities["identity-uuid"]["subscriptions"],
            ["PMTCT", "Loss", "Public", "Prebirth 3", "Postbirth"],
        )

        process_subscription(identities, "identity-uuid", "irrelevant_name")
        self.assertEqual(
            identities["identity-uuid"]["subscriptions"],
            ["PMTCT", "Loss", "Public", "Prebirth 3", "Postbirth"],
        )


class DeduplicateMSISDNsTests(TestCase):
    def test_info_combined(self):
        """
        If there are 2 identities with the same msisdn, their info should be combined
        """
        self.assertEqual(
            deduplicate_msisdns(
                OrderedDict(
                    (
                        (
                            "identity1",
                            {
                                "msisdns": ["+27820001001"],
                                "item1": "value1",
                                "listitem": ["list1"],
                            },
                        ),
                        (
                            "identity2",
                            {
                                "msisdns": ["+27820001001"],
                                "item2": "value2",
                                "listitem": ["list2"],
                            },
                        ),
                    )
                )
            ),
            {
                "+27820001001": {
                    "msisdn": "+27820001001",
                    "item1": "value1",
                    "item2": "value2",
                    "listitem": ["list1", "list2"],
                }
            },
        )
