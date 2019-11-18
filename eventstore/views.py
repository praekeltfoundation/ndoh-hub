from datetime import datetime

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    Event,
    Message,
    OptOut,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from eventstore.serializers import (
    BabySwitchSerializer,
    ChannelSwitchSerializer,
    CHWRegistrationSerializer,
    OptOutSerializer,
    PostbirthRegistrationSerializer,
    PrebirthRegistrationSerializer,
    PublicRegistrationSerializer,
)
from ndoh_hub.utils import TokenAuthQueryString, validate_signature


class MessagesViewSet(GenericViewSet):
    queryset = Message.objects.all()
    permission_classes = (DjangoModelPermissions,)
    authentication_classes = (TokenAuthQueryString, TokenAuthentication)

    def create(self, request):
        validate_signature(request)
        webhook_type = request.headers.get("X-Turn-Hook-Subscription", None)
        if webhook_type == "whatsapp":
            for inbound in request.data.get("messages", []):
                id = inbound.pop("id")
                contact_id = inbound.pop("from")
                type = inbound.pop("type")
                timestamp = datetime.fromtimestamp(int(inbound.pop("timestamp")))

                Message.objects.create(
                    id=id,
                    contact_id=contact_id,
                    type=type,
                    data=inbound,
                    message_direction=Message.INBOUND,
                    created_by=request.user.username,
                    timestamp=timestamp,
                )

            for statuses in request.data.get("statuses", []):
                message_id = statuses.pop("id")
                recipient_id = statuses.pop("recipient_id")
                timestamp = datetime.fromtimestamp(int(statuses.pop("timestamp")))
                message_status = statuses.pop("status")
                Event.objects.create(
                    message_id=message_id,
                    recipient_id=recipient_id,
                    timestamp=timestamp,
                    status=message_status,
                    created_by=request.user.username,
                    data=statuses,
                )

        elif webhook_type == "turn":
            outbound = request.data
            data = {
                "text": outbound["text"],
                "render_mentions": outbound["render_mentions"],
                "preview_url": outbound["preview_url"],
            }
            Message.objects.create(
                id=request.headers["X-WhatsApp-Id"],
                contact_id=outbound["to"],
                type=outbound["type"],
                data=data,
                message_direction=Message.OUTBOUND,
                created_by=request.user.username,
                recipient_type=outbound["recipient_type"],
            )
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_201_CREATED)


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


class CHWRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = CHWRegistration.objects.all()
    serializer_class = CHWRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)


class PrebirthRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PrebirthRegistration.objects.all()
    serializer_class = PrebirthRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)


class PostbirthRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PostbirthRegistration.objects.all()
    serializer_class = PostbirthRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)
