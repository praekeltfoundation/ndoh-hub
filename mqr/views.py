import random

from rest_framework import generics, permissions
from rest_framework.response import Response


class RandomArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # TODO: change this to the strata sequential assignment
        random_arm = random.choice(["ARM", "RCM", "BCM", "RCM_BCM", "RCM_SMS"])
        return Response({"random_arm": random_arm})
