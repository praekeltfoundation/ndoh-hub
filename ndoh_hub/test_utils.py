from unittest import TestCase

import responses

from ndoh_hub.utils import (
    normalise_msisdn,
)
from ndoh_hub.utils_tests import mock_get_messageset_by_shortname, mock_get_schedule


class TestNormaliseMsisdn(TestCase):
    def test_normalise_msisdn(self):
        """
        Normalises the input string into E164 format
        """
        self.assertEqual(normalise_msisdn("082 000 1001"), "+27820001001")
        self.assertEqual(normalise_msisdn("27820001001"), "+27820001001")
        self.assertEqual(normalise_msisdn("+27820001001"), "+27820001001")
