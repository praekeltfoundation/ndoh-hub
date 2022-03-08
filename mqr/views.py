import random

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from mqr.serializers import FaqSerializer, NextMessageSerializer
from mqr.utils import (
    get_age_bucket,
    get_facility_province,
    get_message_details,
    get_next_send_date,
    get_tag,
    get_weeks_pregnant,
)

from .models import MqrStrata
from .serializers import MqrStrataSerializer

STUDY_ARMS = ["ARM", "RCM", "BCM", "RCM_BCM", "RCM_SMS"]


class RandomStrataArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MqrStrataSerializer

    def post(self, request):
        serializer = MqrStrataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # use facility code and look up on db for province
        facility_code = serializer.validated_data.get("facility_code")
        estimated_delivery_date = serializer.validated_data.get(
            "estimated_delivery_date"
        )
        mom_age = serializer.validated_data.get("mom_age")

        clinic_code = get_facility_province(facility_code)
        weeks_pregnant_bucket = get_weeks_pregnant(estimated_delivery_date)
        age_bucket = get_age_bucket(mom_age)

        if clinic_code and weeks_pregnant_bucket and age_bucket:
            province = clinic_code.province

            strata, created = MqrStrata.objects.get_or_create(
                province=province,
                weeks_pregnant_bucket=weeks_pregnant_bucket,
                age_bucket=age_bucket,
            )

            if created:
                random.shuffle(STUDY_ARMS)
                random_arms = STUDY_ARMS
                strata.order = ",".join(random_arms)
            else:
                random_arms = strata.order.split(",")

            arm = random_arms[strata.next_index]

            if strata.next_index + 1 == len(random_arms):
                strata.delete()
            else:
                strata.next_index += 1
                strata.save()

            return Response({"random_arm": arm})
        return Response(status=status.HTTP_400_BAD_REQUEST)


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
