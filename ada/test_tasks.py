from unittest.mock import patch

from django.test import TestCase as DjangoTestCase
from django.test import override_settings

from .tasks import submit_whatsappid_to_rapidpro


class HandleSubmitShatsappidToRapidpro(DjangoTestCase):
    @override_settings(ADA_PROTOTYPE_SURVEY_FLOW_ID="test-flow-uuid")
    def test_submit_whatsappid_to_rapidpro(self):
        """
        Triggers the correct flow with the correct details
        """
        whatsappid = "+27820001001"

        with patch("ada.tasks.rapidpro") as p:
            submit_whatsappid_to_rapidpro(whatsappid)
        p.create_flow_start.delay.assert_called_once_with(
            extra={}, flow="test-flow-uuid", urns=["whatsapp:27820001001"]
        )
