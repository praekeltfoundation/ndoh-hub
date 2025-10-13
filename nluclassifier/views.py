import logging

from django.http import HttpRequest
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .tasks import process_feedback_for_labeling

logger = logging.getLogger(__name__)


class LabelFeedbackView(generics.GenericAPIView):
    """
    Handles inbound messages via a POST request
    Classifies the message using NLU and labels it in Turn

    Access requires authentication via permissions.IsAuthenticated
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request: HttpRequest, *args, **kwargs):
        """
        Processes the POST request from RapidPro
        """

        message_id = request.data.get("message_id")
        inbound_message = request.data.get("inbound_message")

        if not message_id or not inbound_message:
            logger.error(
                "Received request missing 'message_id' or "
                "'inbound_message' in POST body."
            )
            return Response(
                {
                    "error": (
                        "Missing 'message_id' or "
                        "'inbound_message' parameter in POST body."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        process_feedback_for_labeling.delay(message_id, inbound_message)

        logger.info(f"Queued NLU task for message ID: {message_id}")
        return Response(
            {"status": "Feedback labeling process initiated successfully."},
            status=status.HTTP_202_ACCEPTED,
        )
