import random

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from mqr.serializers import FaqSerializer, NextMessageSerializer
from mqr.utils import get_message_details, get_next_send_date, get_tag


class RandomArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # TODO: change this to the strata sequential assignment
        random_arm = random.choice(["ARM", "RCM", "BCM", "RCM_BCM", "RCM_SMS"])
        return Response({"random_arm": random_arm})


class NextMessageView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Gets the next message that we need to send from the content repo
        """
        serializer = NextMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        edd_or_dob_date = serializer.validated_data.get("edd_or_dob_date")
        subscription_type = serializer.validated_data.get("subscription_type")
        arm = serializer.validated_data.get("arm")
        sequence = serializer.validated_data.get("sequence")

        tag = get_tag(arm, subscription_type, edd_or_dob_date, sequence)

        response = get_message_details(tag)

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        response["next_send_date"] = get_next_send_date()
        response["tag"] = tag
        return Response(response, status=status.HTTP_200_OK)


class FaqView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Get FAQ from content repo based on tag and faq number
        """
        serializer = FaqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data.get("tag")
        faq_number = serializer.validated_data.get("faq_number")

        faq_tag = f"{tag}_faq{faq_number}"
        response = get_message_details(faq_tag)

        return Response(response, status=status.HTTP_200_OK)
