import random

from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import MqrStrata
from .serializers import MqrStrataSerializer

STUDY_ARMS = ["ARM", "RCM", "BCM", "RCM_BCM", "RCM_SMS"]


class RandomStrataArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MqrStrataSerializer

    def post(self, request):
        serializer = MqrStrataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        province = serializer.validated_data.get("province")
        weeks_pregnant_bucket = serializer.validated_data.get("weeks_pregnant_bucket")
        age_bucket = serializer.validated_data.get("age_bucket")

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

        if strata.next_index == len(random_arms):
            strata.delete()
        else:
            strata.next_index += 1
            strata.save()

        return Response(arm)
