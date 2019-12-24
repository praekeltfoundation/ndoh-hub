from datetime import datetime

from django.conf import settings
from pytz import UTC
from rest_framework import serializers, status
from rest_framework.authentication import TokenAuthentication
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
    MSISDNSwitch,
    OptOut,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from eventstore.serializers import (
    BabySwitchSerializer,
    ChannelSwitchSerializer,
    CHWRegistrationSerializer,
    MSISDNSwitchSerializer,
    OptOutSerializer,
    PostbirthRegistrationSerializer,
    PrebirthRegistrationSerializer,
    PublicRegistrationSerializer,
    TurnOutboundSerializer,
    WhatsAppWebhookSerializer,
)
from eventstore.whatsapp_actions import handle_outbound
from ndoh_hub.utils import TokenAuthQueryString, validate_signature


class MessagesViewSet(GenericViewSet):
    """
    Receives webhooks in the [format specified by Turn][format] and stores them.

    Supports the `turn` and `whatsapp` webhook types.

    Requires authentication token, either in the `Authorization` header, or in the
    value of the `token` query string.

    [format]: https://whatsapp.praekelt.org/docs/index.html#webhooks
    """

    queryset = Message.objects.all()
    permission_classes = (DjangoModelPermissions,)
    authentication_classes = (TokenAuthQueryString, TokenAuthentication)
    serializer_class = serializers.Serializer

    def create(self, request):
        validate_signature(request)
        try:
            webhook_type = request.headers["X-Turn-Hook-Subscription"]
        except KeyError:
            return Response(
                {"X-Turn-Hook-Subscription": ["This header is required."]},
                status.HTTP_400_BAD_REQUEST,
            )

        if webhook_type == "whatsapp":
            WhatsAppWebhookSerializer(data=request.data).is_valid(raise_exception=True)
            for inbound in request.data.get("messages", []):
                id = inbound.pop("id")
                contact_id = inbound.pop("from")
                type = inbound.pop("type")
                timestamp = datetime.fromtimestamp(
                    int(inbound.pop("timestamp")), tz=UTC
                )

                Message.objects.update_or_create(
                    id=id,
                    defaults={
                        "contact_id": contact_id,
                        "type": type,
                        "data": inbound,
                        "message_direction": Message.INBOUND,
                        "created_by": request.user.username,
                        "timestamp": timestamp,
                    },
                )

            for statuses in request.data.get("statuses", []):
                message_id = statuses.pop("id")
                recipient_id = statuses.pop("recipient_id")
                timestamp = datetime.fromtimestamp(
                    int(statuses.pop("timestamp")), tz=UTC
                )
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
            TurnOutboundSerializer(data=request.data).is_valid(raise_exception=True)
            outbound = request.data
            contact_id = outbound.pop("to")
            type = outbound.pop("type", "")
            try:
                message_id = request.headers["X-WhatsApp-Id"]
            except KeyError:
                return Response(
                    {"X-WhatsApp-Id": ["This header is required."]},
                    status.HTTP_400_BAD_REQUEST,
                )

            msg, created = Message.objects.update_or_create(
                id=message_id,
                defaults={
                    "contact_id": contact_id,
                    "type": type,
                    "data": outbound,
                    "message_direction": Message.OUTBOUND,
                    "created_by": request.user.username,
                },
            )
            if settings.ENABLE_EVENTSTORE_WHATSAPP_ACTIONS and created:
                handle_outbound(msg)
        else:
            return Response(
                {
                    "X-Turn-Hook-Subscription": [
                        f'"{webhook_type}" is not a valid choice for this header.'
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
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


class MSISDNSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = MSISDNSwitch.objects.all()
    serializer_class = MSISDNSwitchSerializer
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
