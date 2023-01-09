import random

from django.conf import settings
from django.http import Http404, JsonResponse
from django_filters import rest_framework as filters
from rest_framework import generics, permissions, status
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from eventstore.views import CursorPaginationFactory
from mqr.serializers import (
    FaqMenuSerializer,
    FaqSerializer,
    FirstSendDateSerializer,
    MqrEndlineChecksSerializer,
    NextMessageSerializer,
)
from mqr.utils import (
    get_age_bucket,
    get_facility_province,
    get_faq_menu,
    get_faq_message,
    get_first_send_date,
    get_next_message,
    get_weeks_pregnant,
    is_study_active_for_weeks_pregnant,
)
from ndoh_hub.utils import rapidpro

from .models import BaselineSurveyResult, MqrStrata
from .serializers import BaselineSurveyResultSerializer, MqrStrataSerializer

STUDY_ARMS = ["ARM", "RCM", "RCM_BCM", "RCM_SMS"]


class RandomStrataArmView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MqrStrataSerializer

    def post(self, request):
        serializer = MqrStrataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # use facility code and look up on db for province
        facility_code = serializer.validated_data.get("facility_code")
        estimated_delivery_date = serializer.validated_data.get(
            "estimated_delivery_date"
        )
        mom_age = serializer.validated_data.get("mom_age")

        if not is_study_active_for_weeks_pregnant(estimated_delivery_date):
            return Response(
                {"Excluded": True, "reason": "study not active for weeks pregnant"}
            )

        clinic_code = get_facility_province(facility_code)
        weeks_pregnant_bucket = get_weeks_pregnant(estimated_delivery_date)
        age_bucket = get_age_bucket(mom_age)

        if clinic_code and weeks_pregnant_bucket and age_bucket:
            province = clinic_code.province

            strata, created = MqrStrata.objects.get_or_create(
                province=province,
                weeks_pregnant_bucket=weeks_pregnant_bucket,
                age_bucket=age_bucket,
            )

            if created:
                random.shuffle(STUDY_ARMS)
                random_arms = STUDY_ARMS
                strata.order = ",".join(random_arms)
            else:
                random_arms = strata.order.split(",")

            arm = random_arms[strata.next_index]

            if strata.next_index + 1 == len(random_arms):
                strata.delete()
            else:
                strata.next_index += 1
                strata.save()

            return Response({"random_arm": arm})
        clinic = clinic_code.code if clinic_code else None
        return Response(
            {
                "Excluded": True,
                "reason": f"clinic: {clinic}, weeks: {weeks_pregnant_bucket}, "
                f"age: {mom_age}",
            }
        )


class BaseMessageView(generics.GenericAPIView):
    def get_tracking_data(self, serializer, message_type):
        return {
            "data__contact_uuid": str(serializer.validated_data.get("contact_uuid")),
            "data__run_uuid": str(serializer.validated_data.get("run_uuid")),
            "data__mqr": message_type,
        }


class NextMessageView(BaseMessageView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Gets the next message that we need to send from the content repo
        """
        serializer = NextMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        edd_or_dob_date = serializer.validated_data.get("edd_or_dob_date")
        subscription_type = serializer.validated_data.get("subscription_type")
        arm = serializer.validated_data.get("arm")
        mom_name = serializer.validated_data.get("mom_name")
        sequence = serializer.validated_data.get("sequence")

        response = get_next_message(
            edd_or_dob_date,
            subscription_type,
            arm,
            sequence,
            mom_name,
            self.get_tracking_data(serializer, "scheduled"),
        )

        if "error" in response:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)


class FaqView(BaseMessageView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Get FAQ from content repo based on tag and faq number
        """
        serializer = FaqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data.get("tag").lower()
        faq_number = serializer.validated_data.get("faq_number")
        viewed = serializer.validated_data.get("viewed", [])

        response = get_faq_message(
            tag,
            faq_number,
            viewed,
            self.get_tracking_data(serializer, "faq"),
        )

        return Response(response, status=status.HTTP_200_OK)


class FaqMenuView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Get FAQ MENU from content repo based on tag
        """
        serializer = FaqMenuSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data.get("tag").lower()
        menu_offset = serializer.validated_data.get("menu_offset", 0)

        tag = tag.replace("_bcm_", "_")

        menu, faq_numbers = get_faq_menu(tag, [], False, menu_offset)

        response = {"menu": menu, "faq_numbers": faq_numbers}

        return Response(response, status=status.HTTP_200_OK)


class BaselineSurveyResultFilter(filters.FilterSet):
    updated_at_gt = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gt")

    class Meta:
        model = BaselineSurveyResult
        fields: list = ["msisdn"]


class BaselineSurveyResultViewSet(
    GenericViewSet,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    queryset = BaselineSurveyResult.objects.all()
    serializer_class = BaselineSurveyResultSerializer
    pagination_class = CursorPaginationFactory("updated_at")
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = BaselineSurveyResultFilter

    def create(self, request):
        serializer = BaselineSurveyResultSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            data = serializer.validated_data.copy()
            data["created_by"] = request.user.username

            obj, created = BaselineSurveyResult.objects.update_or_create(
                msisdn=data["msisdn"], defaults=data
            )
            code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return JsonResponse(BaselineSurveyResultSerializer(obj).data, status=code)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FirstSendDateView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Get First send date based on EDD or baby DOB date
        """
        serializer = FirstSendDateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        edd_or_dob_date = serializer.validated_data.get("edd_or_dob_date")

        first_send_date = get_first_send_date(edd_or_dob_date)

        response = {"first_send_date": first_send_date}

        return Response(response, status=status.HTTP_200_OK)


class MqrEndlineChecksViewSet(generics.GenericAPIView):

    # Lookup contact

    def post(self, request, *args, **kwargs):

        serializer = MqrEndlineChecksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wa_id = serializer.validated_data.get("msisdn").replace("+", "")

        contact = rapidpro.get_contacts(urn=f"whatsapp:{wa_id}").first()

        # Contact not found
        if contact is None:
            raise Http404()

        if contact.fields.get("endline_airtime_received", "FALSE") == "TRUE":
            return Response(
                {"error": "Airtime already received"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not contact.fields.get("mqr_arm"):
            raise Http404()

        self.start_topup_flow(wa_id)

        return_data = {"uuid": contact.uuid}
        return Response(return_data, status=status.HTTP_202_ACCEPTED)

    def start_topup_flow(self, whatsapp_id):
        if rapidpro and settings.MQR_SEND_AIRTIME_FLOW_ID:
            return rapidpro.create_flow_start(
                extra={},
                flow=settings.MQR_SEND_AIRTIME_FLOW_ID,
                urns=[f"whatsapp:{whatsapp_id.lstrip('+')}"],
            )
