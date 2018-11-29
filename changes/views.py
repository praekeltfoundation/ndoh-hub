import base64
import hmac
from hashlib import sha256

import django_filters
import django_filters.rest_framework as filters
import phonenumbers
from django.conf import settings
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from seed_services_client.stage_based_messaging import (  # noqa
    StageBasedMessagingApiClient,
)

from changes import tasks
from ndoh_hub.utils import TokenAuthQueryString

from .models import Change, Source
from .serializers import (
    AdminChangeSerializer,
    AdminOptoutSerializer,
    ChangeSerializer,
    ReceiveEngageMessage,
    ReceiveWhatsAppEventSerializer,
    ReceiveWhatsAppSystemEventSerializer,
    SeedMessageSenderHookSerializer,
)


class CreatedAtCursorPagination(CursorPagination):
    ordering = "-created_at"


class ChangePost(mixins.CreateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer

    def post(self, request, *args, **kwargs):
        # load the users sources - posting users should only have one source
        source = Source.objects.get(user=self.request.user)
        request.data["source"] = source.id
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ChangeFilter(filters.FilterSet):
    """Filter for changes created, using ISO 8601 formatted dates"""

    created_before = django_filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    created_after = django_filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )

    class Meta:
        model = Change
        ("action", "registrant_id", "validated", "source", "created_at")
        fields = [
            "action",
            "registrant_id",
            "validated",
            "source",
            "created_before",
            "created_after",
        ]


class ChangeGetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Changes to be viewed.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer
    filterset_class = ChangeFilter
    pagination_class = CreatedAtCursorPagination


class OptOutInactiveIdentity(APIView):
    """
    Creates an Opt-out Change for an identity we can't send messages to
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            # The hooks send the request data as {"hook":{}, "data":{}}
            data = request.data["data"]
        except KeyError:
            raise ValidationError('"data" must be supplied')
        identity_id = data.get("identity_id", None)
        if identity_id is None or identity_id == "":
            raise ValidationError('"identity_id" must be supplied')
        source = Source.objects.get(user=request.user)
        Change.objects.create(
            source=source,
            registrant_id=identity_id,
            action="momconnect_nonloss_optout",
            data={"reason": "sms_failure"},
        )
        return Response(status=status.HTTP_201_CREATED)


def get_or_create_source(request):
    source, created = Source.objects.get_or_create(
        user=request.user,
        defaults={
            "authority": "advisor",
            "name": (request.user.get_full_name() or request.user.username),
        },
    )
    return source


class ReceiveAdminOptout(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminOptoutSerializer

    def post(self, request, *args, **kwargs):

        admin_serializer = AdminOptoutSerializer(data=request.data)
        if admin_serializer.is_valid():
            identity_id = admin_serializer.validated_data["registrant_id"]
        else:
            return Response(admin_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        sbm_client = StageBasedMessagingApiClient(
            api_url=settings.STAGE_BASED_MESSAGING_URL,
            auth_token=settings.STAGE_BASED_MESSAGING_TOKEN,
        )

        active_subs = sbm_client.get_subscriptions(
            {"identity": identity_id, "active": True}
        )["results"]

        actions = set()
        for sub in active_subs:
            messageset = sbm_client.get_messageset(sub["messageset"])
            if "nurseconnect" in messageset["short_name"]:
                actions.add("nurse_optout")
            elif "pmtct" in messageset["short_name"]:
                actions.add("pmtct_nonloss_optout")
            elif "momconnect" in messageset["short_name"]:
                actions.add("momconnect_nonloss_optout")

        source = get_or_create_source(self.request)

        request.data["source"] = source.id

        changes = []
        for action in actions:
            change = {
                "registrant_id": str(identity_id),
                "action": action,
                "data": {"reason": "other"},
                "source": source.id,
            }
            changes.append(change)

        serializer = ChangeSerializer(data=changes, many=True)

        if serializer.is_valid():
            serializer.save()

            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReceiveAdminChange(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AdminChangeSerializer

    def post(self, request, *args, **kwargs):

        admin_serializer = AdminChangeSerializer(data=request.data)
        if admin_serializer.is_valid():
            data = admin_serializer.validated_data
        else:
            return Response(admin_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source = get_or_create_source(self.request)

        change = {
            "registrant_id": str(data["registrant_id"]),
            "action": "admin_change_subscription",
            "data": {"subscription": str(data["subscription"])},
            "source": source.id,
        }

        if data.get("messageset"):
            change["data"]["messageset"] = data["messageset"]

        if data.get("language"):
            change["data"]["language"] = data["language"]

        serializer = ChangeSerializer(data=change)

        if serializer.is_valid():
            serializer.save()

            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReceiveWhatsAppBase(generics.GenericAPIView):
    permission_classes = (IsAuthenticated, DjangoModelPermissions)
    queryset = Change.objects.none()
    authentication_classes = (TokenAuthQueryString, TokenAuthentication)

    def validate_signature(self, request):
        secret = settings.ENGAGE_HMAC_SECRET
        signature = request.META.get("HTTP_X_ENGAGE_HOOK_SIGNATURE")

        if not signature:
            raise AuthenticationFailed("X-Engage-Hook-Signature header required")

        h = hmac.new(secret.encode(), request.body, sha256)

        if base64.b64encode(h.digest()) != signature.encode():
            raise AuthenticationFailed("Invalid hook signature")


class ReceiveWhatsAppEvent(ReceiveWhatsAppBase):
    serializer_class = ReceiveWhatsAppEventSerializer

    def post(self, request, *args, **kwargs):
        self.validate_signature(request)

        webhook_type = request.META.get("HTTP_X_ENGAGE_HOOK_SUBSCRIPTION", "whatsapp")
        if webhook_type == "whatsapp":
            serializer = ReceiveWhatsAppEventSerializer(data=request.data)
        elif webhook_type == "engage":
            serializer = ReceiveEngageMessage(data=request.data)
        else:
            raise ValidationError(
                "Unrecognised hook subscription {}".format(webhook_type)
            )

        if not serializer.is_valid():
            # If this isn't an event that we care about
            return Response(status=status.HTTP_204_NO_CONTENT)

        if webhook_type == "whatsapp":
            for item in serializer.validated_data["statuses"]:
                tasks.process_whatsapp_unsent_event.delay(
                    item["id"], request.user.pk, item["errors"]
                )
        else:
            message_id = request.META.get("HTTP_X_WHATSAPP_ID")
            if not message_id:
                raise ValidationError("X-WhatsApp-Id header required")
            tasks.process_engage_helpdesk_outbound.delay(
                serializer.validated_data["_vnd"]["v1"]["chat"]["owner"], message_id
            )

        return Response(status=status.HTTP_202_ACCEPTED)


class ReceiveWhatsAppSystemEvent(ReceiveWhatsAppBase):
    serializer_class = ReceiveWhatsAppSystemEventSerializer

    def post(self, request, *args, **kwargs):
        self.validate_signature(request)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        for item in serializer.validated_data["events"]:
            tasks.process_whatsapp_system_event.delay(item["message_id"], item["type"])

        return Response(status=status.HTTP_202_ACCEPTED)


class ReceiveWhatsAppTimeoutSystemEvent(ReceiveWhatsAppBase):
    serializer_class = ReceiveWhatsAppSystemEventSerializer

    def post(self, request, *args, **kwargs):
        self.validate_signature(request)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        for item in serializer.validated_data["statuses"]:
            for error in serializer.validated_data["errors"]:
                tasks.process_whatsapp_timeout_system_event.delay(
                    item["id"], item["timestamp"], item["recipient_id"], item["errors"]
                )

        return Response(status=status.HTTP_202_ACCEPTED)


class SeedMessageSenderHook(generics.GenericAPIView):
    """
    Receives events from the Seed Message Sender. Supports:
    * whatsapp.failed_contact_check

    Requires token auth in the querystring "token" field.
    """

    serializer_class = SeedMessageSenderHookSerializer
    authentication_classes = (TokenAuthQueryString,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msisdn = serializer.validated_data["data"]["address"]
        msisdn = phonenumbers.format_number(msisdn, phonenumbers.PhoneNumberFormat.E164)
        tasks.process_whatsapp_contact_check_fail.delay(str(request.user.pk), msisdn)
        return Response(status=status.HTTP_202_ACCEPTED)
