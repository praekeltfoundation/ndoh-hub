import json
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.urls import reverse

from .tasks import (
    post_to_topup_endpoint,
    submit_whatsappid_to_rapidpro,
    submit_whatsappid_to_rapidpro_topup,
)


class HandleSubmitShatsappidToRapidpro(DjangoTestCase):
    @override_settings(ADA_PROTOTYPE_SURVEY_FLOW_ID="test-flow-uuid")
    def test_submit_whatsappid_to_rapidpro(self):
        """
        Triggers the correct flow with the correct details
        """
        whatsappid = "+27820001001"

        with patch("ada.tasks.rapidpro") as p:
            submit_whatsappid_to_rapidpro(whatsappid)
        p.create_flow_start.assert_called_once_with(
            extra={}, flow="test-flow-uuid", urns=["whatsapp:27820001001"]
        )

    @override_settings(ADA_TOPUP_FLOW_ID="test-flow-uuid")
    def test_submit_whatsappid_to_rapidpro_topup(self):
        """
        Triggers the topup flow with the correct details
        """
        whatsappid = "+27820001001"

        with patch("ada.tasks.rapidpro") as p:
            submit_whatsappid_to_rapidpro_topup(whatsappid)
        p.create_flow_start.assert_called_once_with(
            extra={}, flow="test-flow-uuid", urns=["whatsapp:27820001001"]
        )

    @override_settings(ADA_TOPUP_AUTHORIZATION_TOKEN="token")
    @patch("requests.post")
    def test_post_to_topup_endpoint(self, mock_post):
        """
        Post request to the topup endpoint with the whatsappid
        """
        whatsappid = "+27820001001"
        payload = {"whatsappid": whatsappid}
        head = {"Authorization": "Token " + "token", "Content-Type": "application/json"}
        url = reverse("rapidpro_topup_flow")
        post_to_topup_endpoint(whatsappid)
        mock_post.assert_called_with(
            url, data=json.dumps(payload), headers=head
        )
