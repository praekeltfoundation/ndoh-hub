from rest_framework import generics
from rest_framework.response import Response

from ndoh_hub.serializers import WhatsappTemplateMessageSerializer
from ndoh_hub.utils import send_whatsapp_template_message


class SendWhatsappTemplateView(generics.GenericAPIView):
    def post(self, request):
        """
        Send a Whatsapp template
        """
        serializer = WhatsappTemplateMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msisdn = serializer.validated_data.get("msisdn")
        template_name = serializer.validated_data.get("template_name")
        parameters = serializer.validated_data.get("parameters", [])
        media = serializer.validated_data.get("media")
        save_status_record = serializer.validated_data.get("save_status_record")

        preferred_channel, status_id = send_whatsapp_template_message(
            msisdn, template_name, parameters, media, save_status_record
        )

        return Response(
            {"preferred_channel": preferred_channel, "status_id": status_id}
        )
