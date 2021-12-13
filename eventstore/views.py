from datetime import datetime

from django.conf import settings
from django.db import IntegrityError
from django.http import Http404
from django_filters import rest_framework as filters
from pytz import UTC
from rest_framework import generics, permissions, serializers, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    Covid19TriageStart,
    DBEOnBehalfOfProfile,
    EddSwitch,
    Event,
    Feedback,
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
)
from eventstore.serializers import (
    AdaAssessmentNotificationSerializer,
    AdaObservationSerializer,
    AdaPatientSerializer,
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
    EddSwitchSerializer,
    FeedbackSerializer,
    ForgetContactSerializer,
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
    WhatsAppWebhookSerializer,
)
from eventstore.tasks import (
    forget_contact,
    process_ada_assessment_notification,
    reset_delivery_failure,
)
from eventstore.whatsapp_actions import handle_event, handle_inbound, handle_outbound
from ndoh_hub.utils import TokenAuthQueryString, validate_signature
from registrations.views import CursorPaginationFactory


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
    permission_classes = (DjangoViewModelPermissions,)

    def perform_create(self, serializer):
        optout = serializer.save()
        if optout.optout_type == OptOut.FORGET_TYPE:
            forget_contact.delay(str(optout.contact_id))


class ForgetContactView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = ForgetContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_id = serializer.validated_data.get("contact_id")

        forget_contact.delay(str(contact_id))

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


class AdaAssessmentNotificationViewSet(ViewSet):
    # This ultimately creates a Covid19Triage (through the task), so relate permissions
    queryset = Covid19Triage.objects.none()
    permission_classes = (DjangoViewModelPermissions,)
    authentication_classes = (TokenAuthQueryString,)

    def create(self, request):
        serializer = AdaAssessmentNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient_id = None
        patient_dob = None
        observations = {}
        errors = {}
        # Use request.data here, because the serializer doesn't have all the data that
        # we need for each of the entries
        for i, entry in enumerate(request.data["entry"]):
            resource = entry["resource"]
            resource_type = resource["resourceType"]
            # Because the kind of validation depends on the resource type, we need to
            # do validation manually here, choosing the correct serializer according
            # to the type
            if resource_type == "Patient":
                patient_serializer = AdaPatientSerializer(data=resource)
                if not patient_serializer.is_valid():
                    errors[i] = {"resource": patient_serializer.errors}
                    continue
                patient_id = patient_serializer.validated_data["id"]
                patient_dob = patient_serializer.validated_data["birthDate"]
            elif resource_type == "Observation":
                observation_serializer = AdaObservationSerializer(data=resource)
                if not observation_serializer.is_valid():
                    errors[i] = {"resource": observation_serializer.errors}
                    continue
                observation = observation_serializer.validated_data
                observations[observation["code"]["text"].strip().lower()] = observation[
                    "valueBoolean"
                ]
        if errors:
            raise ValidationError({"entry": errors})
        # Ensure that we extracted all the data that we need
        if not patient_id:
            raise ValidationError({"entry": ["No patient entry found"]})
        missing_observations = {"fever", "cough", "sore throat"} - set(
            observations.keys()
        )
        if missing_observations:
            raise ValidationError(
                {"entry": [f"Missing observation {o}" for o in missing_observations]}
            )
        data = {
            "username": request.user.username,
            "id": serializer.validated_data["id"],
            "patient_id": patient_id,
            "patient_dob": patient_dob.isoformat(),
            "observations": observations,
            "timestamp": serializer.validated_data["timestamp"],
        }
        process_ada_assessment_notification.delay(**data)
        return Response(data, status=status.HTTP_202_ACCEPTED)
