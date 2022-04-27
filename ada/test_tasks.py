import json
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.urls import reverse

from ada.tasks import (
    post_to_topup_endpoint,
    start_pdf_flow,
    start_prototype_survey_flow,
    start_topup_flow,
)


class HandleSubmitShatsappidToRapidpro(DjangoTestCase):
    @override_settings(ADA_PROTOTYPE_SURVEY_FLOW_ID="test-flow-uuid")
    def test_start_prototype_survey_flow(self):
        """
        Triggers the correct flow with the correct details
        """
        whatsappid = "+27820001001"

        with patch("ada.tasks.rapidpro") as p:
            start_prototype_survey_flow(whatsappid)
        p.create_flow_start.assert_called_once_with(
            extra={}, flow="test-flow-uuid", urns=["whatsapp:27820001001"]
        )

    @override_settings(ADA_TOPUP_FLOW_ID="test-flow-uuid")
    def test_start_topup_flow(self):
        """
        Triggers the topup flow with the correct details
        """
        whatsappid = "+27820001001"

        with patch("ada.tasks.rapidpro") as p:
            start_topup_flow(whatsappid)
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
        mock_post.assert_called_with(url, data=json.dumps(payload), headers=head)

    @override_settings(ADA_ASSESSMENT_FLOW_ID="test-flow-uuid")
    def test_start_pdf_flow(self):
        """
        Triggers the topup flow with the correct details
        """
        msisdn = "27820001001"
        pdf_media_id = "media-uuid"

        with patch("ada.tasks.rapidpro") as p:
            start_pdf_flow(msisdn, pdf_media_id)
        p.create_flow_start.assert_called_once_with(
            extra={"pdf": pdf_media_id},
            flow="test-flow-uuid",
            urns=["whatsapp:27820001001"],
        )
