from datetime import datetime

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404, JsonResponse
from django_filters import rest_framework as filters
from pytz import UTC
from rest_framework import generics, permissions, serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from eventstore.batch_tasks import bulk_insert_events, update_or_create_message
from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    Covid19TriageStart,
    DBEOnBehalfOfProfile,
    DeliveryFailure,
    EddSwitch,
    Event,
    Feedback,
    HCSStudyBRandomization,
    HealthCheckUserProfile,
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
    WhatsAppTemplateSendStatus,
)
from eventstore.serializers import (
    BabyDobSwitchSerializer,
    BabySwitchSerializer,
    CDUAddressUpdateSerializer,
    ChannelSwitchSerializer,
    CHWRegistrationSerializer,
    Covid19TriageSerializer,
    Covid19TriageStartSerializer,
    Covid19TriageV2Serializer,
    Covid19TriageV3Serializer,
    Covid19TriageV4Serializer,
    DBEOnBehalfOfProfileSerializer,
    DeliveryFailureSerializer,
    EddSwitchSerializer,
    EventSerializer,
    FeedbackSerializer,
    ForgetContactSerializer,
    HCSStudyBRandomizationSerializer,
    HealthCheckUserProfileSerializer,
    IdentificationSwitchSerializer,
    LanguageSwitchSerializer,
    MSISDNSerializer,
    MSISDNSwitchSerializer,
    OptOutSerializer,
    PMTCTRegistrationSerializer,
    PostbirthRegistrationSerializer,
    PrebirthRegistrationSerializer,
    PublicRegistrationSerializer,
    ResearchOptinSwitchSerializer,
    TurnOutboundSerializer,
    WhatsAppTemplateSendStatusSerializer,
    WhatsAppWebhookSerializer,
)
from eventstore.tasks import forget_contact, reset_delivery_failure
from eventstore.whatsapp_actions import handle_event, increment_failure_count
from ndoh_hub.utils import TokenAuthQueryString, validate_signature


def CursorPaginationFactory(field):
    """
    Returns a CursorPagination class with the field specified by field
    """

    class CustomCursorPagination(CursorPagination):
        ordering = field

    name = f"{field.capitalize()}CursorPagination"
    CustomCursorPagination.__name__ = name
    CustomCursorPagination.__qualname__ = name

    return CustomCursorPagination


class DjangoViewModelPermissions(DjangoModelPermissions):
    # DjangoModelPermissions, but also with a restriction on viewing data
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class MessagesViewSet(GenericViewSet):
    """
    Receives webhooks in the [format specified by Turn][format] and stores them.

    Supports the `turn` and `whatsapp` webhook types.

    Requires authentication token, either in the `Authorization` header, or in the
    value of the `token` query string.

    [format]: https://whatsapp.praekelt.org/docs/index.html#webhooks
    """

    queryset = Message.objects.all()
    permission_classes = (DjangoViewModelPermissions,)
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

                update_or_create_message.delay(
                    id,
                    {
                        "contact_id": contact_id,
                        "type": type,
                        "data": inbound,
                        "message_direction": Message.INBOUND,
                        "created_by": request.user.username,
                        "timestamp": timestamp,
                        "fallback_channel": on_fallback_channel,
                    },
                )

            for statuses in request.data.get("statuses", []):
                message_id = statuses.pop("id")

                if "message" in statuses:
                    recipient_id = statuses["message"].pop("recipient_id")
                    if statuses["message"] == {}:
                        statuses.pop("message")
                else:
                    recipient_id = statuses.pop("recipient_id")

                timestamp = datetime.fromtimestamp(
                    int(statuses.pop("timestamp")), tz=UTC
                )
                message_status = statuses.pop("status")

                if settings.BULK_INSERT_EVENTS_ENABLED:
                    bulk_insert_events.delay(
                        message_id=message_id,
                        recipient_id=recipient_id,
                        timestamp=timestamp,
                        status=message_status,
                        created_by=request.user.username,
                        data=statuses,
                        fallback_channel=on_fallback_channel,
                    )
                else:
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

            update_or_create_message.delay(
                message_id,
                {
                    "contact_id": contact_id,
                    "type": type,
                    "data": outbound,
                    "message_direction": Message.OUTBOUND,
                    "created_by": request.user.username,
                    "fallback_channel": on_fallback_channel,
                },
            )

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


class EventFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = Event
        fields: list = ["message_id"]


class WhatsAppEventsViewSet(GenericViewSet, ListModelMixin):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = EventFilter


class OptOutViewSet(GenericViewSet, CreateModelMixin):
    queryset = OptOut.objects.all()
    serializer_class = OptOutSerializer
    permission_classes = (DjangoViewModelPermissions,)

    def perform_create(self, serializer):
        optout = serializer.save()
        if optout.optout_type == OptOut.FORGET_TYPE:
            forget_contact.apply_async(countdown=600, args=[str(optout.contact_id)])


class ForgetContactView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = ForgetContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_id = serializer.validated_data.get("contact_id")

        forget_contact.apply_async(
            countdown=settings.FORGET_OPTOUT_TASK_COUNTDOWN, args=[str(contact_id)]
        )

        return Response({}, status=status.HTTP_200_OK)


class BabySwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = BabySwitch.objects.all()
    serializer_class = BabySwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class ChannelSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = ChannelSwitch.objects.all()
    serializer_class = ChannelSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class MSISDNSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = MSISDNSwitch.objects.all()
    serializer_class = MSISDNSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class LanguageSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = LanguageSwitch.objects.all()
    serializer_class = LanguageSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class IdentificationSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = IdentificationSwitch.objects.all()
    serializer_class = IdentificationSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class ResearchOptinSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = ResearchOptinSwitch.objects.all()
    serializer_class = ResearchOptinSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class BaseRegistrationViewSet(GenericViewSet, CreateModelMixin):
    def perform_create(self, serializer):
        instance = serializer.save()
        reset_delivery_failure.delay(contact_uuid=instance.contact_id)
        return instance


class PublicRegistrationViewSet(BaseRegistrationViewSet):
    queryset = PublicRegistration.objects.all()
    serializer_class = PublicRegistrationSerializer
    permission_classes = (DjangoViewModelPermissions,)


class CHWRegistrationViewSet(BaseRegistrationViewSet):
    queryset = CHWRegistration.objects.all()
    serializer_class = CHWRegistrationSerializer
    permission_classes = (DjangoViewModelPermissions,)


class PrebirthRegistrationViewSet(BaseRegistrationViewSet):
    queryset = PrebirthRegistration.objects.all()
    serializer_class = PrebirthRegistrationSerializer
    permission_classes = (DjangoViewModelPermissions,)


class PostbirthRegistrationViewSet(BaseRegistrationViewSet):
    queryset = PostbirthRegistration.objects.all()
    serializer_class = PostbirthRegistrationSerializer
    permission_classes = (DjangoViewModelPermissions,)


class PMTCTRegistrationViewSet(BaseRegistrationViewSet):
    queryset = PMTCTRegistration.objects.all()
    serializer_class = PMTCTRegistrationSerializer
    permission_classes = (DjangoViewModelPermissions,)


class EddSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = EddSwitch.objects.all()
    serializer_class = EddSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class BabyDobSwitchViewSet(GenericViewSet, CreateModelMixin):
    queryset = BabyDobSwitch.objects.all()
    serializer_class = BabyDobSwitchSerializer
    permission_classes = (DjangoViewModelPermissions,)


class FeedbackViewSet(GenericViewSet, CreateModelMixin):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = (DjangoViewModelPermissions,)


class Covid19TriageFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = Covid19Triage
        fields: list = ["msisdn"]


class Covid19TriageStartFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = Covid19TriageStart
        fields: list = []


class HCSStudyBRandomizationFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = HCSStudyBRandomization
        fields: list = []


class Covid19TriageViewSet(GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = Covid19Triage.objects.all()
    serializer_class = Covid19TriageSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = Covid19TriageFilter

    def perform_create(self, serializer):
        """
        Mark turn healthcheck complete, and update the user profile
        """
        instance = serializer.save()

        profile = HealthCheckUserProfile.objects.get_or_prefill(msisdn=instance.msisdn)
        profile.update_from_healthcheck(instance)
        profile.update_post_screening_study_arms(instance.risk, instance.created_by)
        profile.save()

        if (
            instance.created_by == "whatsapp_dbe_healthcheck"
            and instance.data.get("profile") == "parent"
        ):
            DBEOnBehalfOfProfile.objects.update_or_create_from_healthcheck(instance)

        return instance

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
    returning_user_skipped_fields = {
        "first_name",
        "last_name",
        "province",
        "city",
        "date_of_birth",
        "gender",
        "location",
        "city_location",
        "preexisting_condition",
        "rooms_in_household",
        "persons_in_household",
    }

    def _get_msisdn(self, data):
        """Gets the MSISDN from the data, or raises a ValidationError"""
        serializer = MSISDNSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["msisdn"]

    def _update_data(self, data, triage):
        """Updates the data from the values in triage"""
        for field in self.returning_user_skipped_fields:
            value = getattr(triage, field)
            if value:
                data[field] = value

    def create(self, request, *args, **kwargs):
        # If all of the returning user skipped fields are missing
        if all(not request.data.get(f) for f in self.returning_user_skipped_fields):
            # Get those fields from a previous completed HealthCheck
            msisdn = self._get_msisdn(request.data)
            triage = Covid19Triage.objects.filter(msisdn=msisdn).earliest("timestamp")
            if triage:
                self._update_data(request.data, triage)
        return super().create(request, *args, **kwargs)


class Covid19TriageV3ViewSet(Covid19TriageV2ViewSet):
    serializer_class = Covid19TriageV3Serializer

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class Covid19TriageV4ViewSet(Covid19TriageV3ViewSet):
    serializer_class = Covid19TriageV4Serializer

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class Covid19TriageStartViewSet(GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = Covid19TriageStart.objects.all()
    serializer_class = Covid19TriageStartSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = Covid19TriageStartFilter


class HCSStudyBRandomizationViewSet(GenericViewSet, CreateModelMixin, ListModelMixin):
    queryset = HCSStudyBRandomization.objects.all()
    serializer_class = HCSStudyBRandomizationSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = HCSStudyBRandomizationFilter

    def create(self, request, *args, **kwargs):
        serializer = HCSStudyBRandomizationSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            data = serializer.validated_data
            msisdn = data["msisdn"]
            data["created_by"] = request.user.username
            obj, created = HCSStudyBRandomization.objects.update_or_create(
                msisdn=msisdn, defaults=data
            )
            code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return JsonResponse(HCSStudyBRandomizationSerializer(obj).data, status=code)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckUserProfileViewSet(GenericViewSet, RetrieveModelMixin):
    queryset = HealthCheckUserProfile.objects.all()
    serializer_class = HealthCheckUserProfileSerializer
    permission_classes = (DjangoViewModelPermissions,)

    def get_object(self):
        obj = HealthCheckUserProfile.objects.get_or_prefill(msisdn=self.kwargs["pk"])
        if not obj.pk:
            raise Http404()
        self.check_object_permissions(self.request, obj)
        return obj


class CDUAddressUpdateViewSet(GenericViewSet, CreateModelMixin):
    queryset = CDUAddressUpdate.objects.all()
    serializer_class = CDUAddressUpdateSerializer
    permission_classes = (DjangoViewModelPermissions,)


class DBEOnBehalfOfProfileViewSet(GenericViewSet, ListModelMixin):
    queryset = DBEOnBehalfOfProfile.objects.all()
    serializer_class = DBEOnBehalfOfProfileSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("id")

    def get_queryset(self):
        queryset = self.queryset
        msisdn = self.request.query_params.get("msisdn", None)
        if msisdn is not None:
            queryset = queryset.filter(msisdn=msisdn)
        return queryset


class DeliveryFailureViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin):
    queryset = DeliveryFailure.objects.all()
    serializer_class = DeliveryFailureSerializer
    permission_classes = (DjangoViewModelPermissions,)
    pagination_class = CursorPaginationFactory("timestamp")

    def get_object(self):
        try:
            obj = DeliveryFailure.objects.get(contact_id=self.kwargs["pk"])
        except DeliveryFailure.DoesNotExist as df:
            raise Http404() from df
        self.check_object_permissions(self.request, obj)
        return obj

    def post(self, request, *args, **kwargs):
        serializer = DeliveryFailureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_id = serializer.validated_data.get("contact_id")
        timestamp = serializer.validated_data.get("timestamp")
        reason = OptOut.WHATSAPP_FAILURE_REASON

        created = increment_failure_count(contact_id, timestamp, reason)

        if created:
            return Response({}, status=status.HTTP_201_CREATED)

        return Response({}, status=status.HTTP_200_OK)


class WhatsAppTemplateSendStatusViewSet(
    GenericViewSet, RetrieveModelMixin, UpdateModelMixin
):
    queryset = WhatsAppTemplateSendStatus.objects.all()
    serializer_class = WhatsAppTemplateSendStatusSerializer
    permission_classes = (DjangoViewModelPermissions,)
    filter_backends = [filters.DjangoFilterBackend]
