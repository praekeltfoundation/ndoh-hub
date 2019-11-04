from datetime import datetime

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    Events,
    Messages,
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
from ndoh_hub.utils import validate_signature


class MessagesViewSet(GenericViewSet):
    def create(self, request):
        validate_signature(request)
        try:
            webhook_type = request.META.get("HTTP_X_TURN_HOOK_SUBSCRIPTION", "whatsapp")
            if webhook_type == "whatsapp":
                for inbound in request.data.get("messages", []):
                    data = {
                        "context": inbound.get("context"),
                        "errors": inbound.get("errors"),
                        "audio": inbound.get("audio"),
                        "document": inbound.get("document"),
                        "image": inbound.get("image"),
                        "system": inbound.get("system"),
                        "location": inbound.get("location"),
                        "text": inbound.get("text"),
                        "video": inbound.get("video"),
                        "voice": inbound.get("voice"),
                    }
                    Messages.objects.create(
                        id=inbound["id"],
                        contact_id=inbound["from"],
                        type=inbound["type"],
                        data=data,
                        message_direction=Messages.INBOUND,
                        created_by=request.user.username,
                        recipient_type=inbound["recipient_type"],
                        timestamp=datetime.fromtimestamp(int(inbound["timestamp"])),
                    )

                for statuses in request.data.get("statuses", []):
                    data = {"errors": statuses.get("errors")}
                    Events.objects.create(
                        message_id=statuses.get("id"),
                        recipient_id=statuses.get("recipient_id"),
                        timestamp=datetime.fromtimestamp(
                            int(statuses.get("timestamp"))
                        ),
                        status=statuses.get("status"),
                        created_by=request.user.username,
                        data=data,
                    )

            elif webhook_type == "turn":
                inbound = request.data["messages"]
                data = {
                    "text": inbound.text,
                    "render_mentions": inbound.render_mentions,
                    "preview_url": inbound.preview_url,
                }
                Messages.objects.create(
                    id=request.headers["X-WhatsApp-Id"],
                    contact_id=inbound.to,
                    type=type,
                    data=data,
                    message_direction=inbound.OUTBOUND,
                    created_by=request.user.username,
                    recipient_type=inbound.recipient_type,
                )
            else:
                data = {
                    "text": inbound.text,
                    "render_mentions": inbound.render_mentions,
                    "preview_url": inbound.preview_url,
                }
                Messages.objects.create(
                    id=request.headers["X-WhatsApp-Id"],
                    contact_id=inbound.to,
                    type=type,
                    data=data,
                    message_direction=inbound.OUTBOUND,
                    created_by=request.user.username,
                    recipient_type=inbound.recipient_type,
                )
        except ValidationError:
            raise ValidationError(
                "Unrecognised hook subscription {}".format(webhook_type)
            )

        return Response(status=status.HTTP_202_ACCEPTED)


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
