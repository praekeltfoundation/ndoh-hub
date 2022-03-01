import random

from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import MqrStrata
from .serializers import MqrStrataSerializer

arms = ["ARM", "RCM", "BCM", "RCM_BCM", "RCM_SMS"]


class RandomArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # TODO: change this to the strata sequential assignment
        random_arm = random.choice(arms)
        return Response({"random_arm": random_arm})


class RandomStrataArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MqrStrataSerializer

    def post(self, request):
        serializer = MqrStrataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        province = serializer.validated_data.get("province")
        weeks_pregnant = serializer.validated_data.get("weeks_pregnant")
        age = serializer.validated_data.get("age")

        strata, created = MqrStrata.objects.get_or_create(
            province=province, weeks_pregnant=weeks_pregnant, age=age
        )

        if created:
            random.shuffle(arms)
            random_arms = arms
            strata.order = ",".join(arms)
        else:
            random_arms = strata.order.split(",")

        arm = arms[strata.next_index]

        if strata.next_index == len(random_arms):
            strata.delete()
        else:
            strata.next_index += 1
            strata.save()

        return Response(arm)
