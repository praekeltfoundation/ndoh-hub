from datetime import datetime

from django.conf import settings
from django.db import IntegrityError
from django_filters import rest_framework as filters
from pytz import UTC
from rest_framework import serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    EddSwitch,
    Event,
    IdentificationSwitch,
    LanguageSwitch,
    Message,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)
from eventstore.serializers import (
    BabyDobSwitchSerializer,
    BabySwitchSerializer,
    CDUAddressUpdateSerializer,
    ChannelSwitchSerializer,
    CHWRegistrationSerializer,
    Covid19TriageSerializer,
    Covid19TriageV2Serializer,
    EddSwitchSerializer,
    IdentificationSwitchSerializer,
    LanguageSwitchSerializer,
    MSISDNSwitchSerializer,
    OptOutSerializer,
    PMTCTRegistrationSerializer,
    PostbirthRegistrationSerializer,
    PrebirthRegistrationSerializer,
    PublicRegistrationSerializer,
    ResearchOptinSwitchSerializer,
    TurnOutboundSerializer,
    WhatsAppWebhookSerializer,
)
from eventstore.tasks import forget_contact
from eventstore.whatsapp_actions import handle_event, handle_inbound, handle_outbound
from ndoh_hub.utils import TokenAuthQueryString, validate_signature
from registrations.views import CursorPaginationFactory


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

        on_fallback_channel = request.headers.get("X-Turn-Fallback-Channel", "0") == "1"
        is_turn_event = request.headers.get("X-Turn-Event", "0") == "1"

        if webhook_type == "whatsapp" or is_turn_event:
            WhatsAppWebhookSerializer(data=request.data).is_valid(raise_exception=True)
            for inbound in request.data.get("messages", []):
                id = inbound.pop("id")
                contact_id = inbound.pop("from")
                type = inbound.pop("type")
                timestamp = datetime.fromtimestamp(
                    int(inbound.pop("timestamp")), tz=UTC
                )

                msg, created = Message.objects.update_or_create(
                    id=id,
                    defaults={
                        "contact_id": contact_id,
                        "type": type,
                        "data": inbound,
                        "message_direction": Message.INBOUND,
                        "created_by": request.user.username,
                        "timestamp": timestamp,
                        "fallback_channel": on_fallback_channel,
                    },
                )
                if settings.ENABLE_EVENTSTORE_WHATSAPP_ACTIONS and created:
                    handle_inbound(msg)

            for statuses in request.data.get("statuses", []):
                message_id = statuses.pop("id")
                recipient_id = statuses.pop("recipient_id")
                timestamp = datetime.fromtimestamp(
                    int(statuses.pop("timestamp")), tz=UTC
                )
                message_status = statuses.pop("status")
                event = Event.objects.create(
                    message_id=message_id,
                    recipient_id=recipient_id,
                    timestamp=timestamp,
                    status=message_status,
                    created_by=request.user.username,
                    data=statuses,
                    fallback_channel=on_fallback_channel,
                )

                if settings.ENABLE_EVENTSTORE_WHATSAPP_ACTIONS:
                    handle_event(event)

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
                    "fallback_channel": on_fallback_channel,
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

    def perform_create(self, serializer):
        optout = serializer.save()
        if optout.optout_type == OptOut.FORGET_TYPE:
            forget_contact.delay(str(optout.contact_id))


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


class LanguageSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = LanguageSwitch.objects.all()
    serializer_class = LanguageSwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class IdentificationSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = IdentificationSwitch.objects.all()
    serializer_class = IdentificationSwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class ResearchOptinSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = ResearchOptinSwitch.objects.all()
    serializer_class = ResearchOptinSwitchSerializer
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


class PMTCTRegistrationViewSet(GenericViewSet, CreateModelMixin):
    queryset = PMTCTRegistration.objects.all()
    serializer_class = PMTCTRegistrationSerializer
    permission_classes = (DjangoModelPermissions,)


class EddSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = EddSwitch.objects.all()
    serializer_class = EddSwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class BabyDobSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = BabyDobSwitch.objects.all()
    serializer_class = BabyDobSwitchSerializer
    permission_classes = (DjangoModelPermissions,)


class Covid19TriageFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = Covid19Triage
        fields: list = []


class Covid19TriageViewSet(GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = Covid19Triage.objects.all()
    serializer_class = Covid19TriageSerializer
    permission_classes = (DjangoModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = Covid19TriageFilter

    def create(self, *args, **kwargs):
        try:
            return super().create(*args, **kwargs)
        except IntegrityError:
            # We already have this entry
            return Response(status=status.HTTP_200_OK)

    def get_throttles(self):
        """
        Set the throttle_scope dynamically to get different rates per action
        """
        self.throttle_scope = f"covid19triage.{self.action}"
        return super().get_throttles()


class Covid19TriageV2ViewSet(Covid19TriageViewSet):
    serializer_class = Covid19TriageV2Serializer


class CDUAddressUpdateViewSet(GenericViewSet, CreateModelMixin):
    queryset = CDUAddressUpdate.objects.all()
    serializer_class = CDUAddressUpdateSerializer
    permission_classes = (DjangoModelPermissions,)
