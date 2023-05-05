from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SendWhatsappTemplateTests(APITestCase):
    url = reverse("send-whatsapp-template")

    def test_send_whatsapp_template_unauthorized_user(self):
        """
        unauthorized user access denied
        Returns: status code 401

        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_send_whatsapp_template_message_number_on_whatsapp(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        parameters = {"type": "text", "text": "test template send"}
        namespace = "test"
        msisdn = "+27820001001"
        template_name = "test template"

        response = self.client.post(
            self.url,
            data={
                "msisdn": msisdn,
                "namespace": namespace,
                "template_name": template_name,
                "parameters": parameters,
            },
            format="json",
        )
        breakpoint()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response, "Whataspp")
