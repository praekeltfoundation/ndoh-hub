from unittest import TestCase

from ndoh_hub.utils import normalise_msisdn


class TestNormaliseMsisdn(TestCase):
    def test_normalise_msisdn(self):
        """
        Normalises the input string into E164 format
        """
        self.assertEqual(normalise_msisdn("082 000 1001"), "+27820001001")
        self.assertEqual(normalise_msisdn("27820001001"), "+27820001001")
        self.assertEqual(normalise_msisdn("+27820001001"), "+27820001001")
