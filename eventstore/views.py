from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import GenericViewSet

from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    OptOut,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from eventstore.serializers import (
    BabySwitchSerializer,
    ChannelSwitchSerializer,
    OptOutSerializer,
    PostbirthRegistrationSerializer,
    PrebirthRegistrationSerializer,
    PublicRegistrationSerializer,
)


class OptOutViewSet(GenericViewSet, CreateModelMixin):
    queryset = OptOut.objects.all()
    serializer_class = OptOutSerializer
    permission_classes = (DjangoModelPermissions,)


class BabySwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = BabySwitch.objects.all()
    serializer_class = BabySwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class ChannelSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = ChannelSwitch.objects.all()
    serializer_class = ChannelSwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class PublicRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PublicRegistration.objects.all()
    serializer_class = PublicRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)


class PrebirthRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PrebirthRegistration.objects.all()
    serializer_class = PrebirthRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)


class PostbirthRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PostbirthRegistration.objects.all()
    serializer_class = PostbirthRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)
