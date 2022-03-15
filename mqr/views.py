import random

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from mqr.serializers import FaqSerializer, NextMessageSerializer
from mqr.utils import (
    get_age_bucket,
    get_facility_province,
    get_faq_message,
    get_next_message,
    get_weeks_pregnant,
)

from .models import MqrStrata
from .serializers import MqrStrataSerializer

STUDY_ARMS = ["ARM", "RCM", "BCM", "BCM_RCM", "RCM_SMS"]


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


class BaseMessageView(generics.GenericAPIView):
    def get_tracking_data(self, serializer, message_type):
        return {
            "data__contact_uuid": str(serializer.validated_data.get("contact_uuid")),
            "data__run_uuid": str(serializer.validated_data.get("run_uuid")),
            "data__mqr": message_type,
        }


class NextMessageView(BaseMessageView):
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
        mom_name = serializer.validated_data.get("mom_name")
        sequence = serializer.validated_data.get("sequence")

        response = get_next_message(
            edd_or_dob_date,
            subscription_type,
            arm,
            sequence,
            mom_name,
            self.get_tracking_data(serializer, "scheduled"),
        )

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)


class FaqView(BaseMessageView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Get FAQ from content repo based on tag and faq number
        """
        serializer = FaqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data.get("tag")
        faq_number = serializer.validated_data.get("faq_number")
        viewed = serializer.validated_data.get("viewed", [])

        response = get_faq_message(
            tag,
            faq_number,
            viewed,
            self.get_tracking_data(serializer, "faq"),
        )

        return Response(response, status=status.HTTP_200_OK)
