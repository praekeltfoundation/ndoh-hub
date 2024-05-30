from functools import partial

from django.forms.models import model_to_dict
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response

from ndoh_hub.utils import msisdn_to_whatsapp_id

from .models import ClinicCode, WhatsAppContact
from .serializers import WhatsAppContactCheckSerializer


class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"


class FacilityDetailsView(generics.RetrieveAPIView):

    def get(self, request):
        try:
            facility_code = request.query_params["facility_code"]
        except KeyError:
            return Response(
                {"error": "Must supply 'criteria' query parameter"},
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            clinic = ClinicCode.objects.get(value=facility_code)
        except ClinicCode.DoesNotExist:
            return Response(
                {"error": "Clinic not found"},
                status.HTTP_404_NOT_FOUND,
            )

        return Response(model_to_dict(clinic))


class FacilityCheckView(generics.RetrieveAPIView):
    queryset = ClinicCode.objects.all()
    permission_classes = (DjangoModelPermissions,)
    authentication_classes = (BasicAuthentication, TokenAuthentication)

    def get(self, request: Request) -> Response:
        try:
            field, value = request.query_params["criteria"].split(":")
        except KeyError:
            return Response(
                {"error": "Must supply 'criteria' query parameter"},
                status.HTTP_400_BAD_REQUEST,
            )
        except ValueError:
            return Response(
                {"error": "Criteria query parameter must be in 'field:value' format"},
                status.HTTP_400_BAD_REQUEST,
            )

        results = ClinicCode.objects.filter(**{field: value}).values_list(
            "code", "value", "uid", "name"
        )
        return Response(
            {
                "title": "FacilityCheck",
                "headers": [
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "code",
                        "column": "code",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "value",
                        "column": "value",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "uid",
                        "column": "uid",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "name",
                        "column": "name",
                        "type": "java.lang.String",
                    },
                ],
                "rows": results,
                "width": 4,
                "height": len(results),
            }
        )


class WhatsAppContactCheckViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    authentication_classes = (SessionAuthentication, BearerTokenAuthentication)
    permission_classes = (DjangoModelPermissions,)
    serializer_class = WhatsAppContactCheckSerializer
    queryset = WhatsAppContact.objects.all()

    def get_status(self, msisdn):
        msisdn = msisdn.raw_input
        whatsapp_id = msisdn_to_whatsapp_id(msisdn)

        return {"input": msisdn, "status": "valid", "wa_id": whatsapp_id}

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        results = map(partial(self.get_status), data["contacts"])
        return Response({"contacts": results}, status=status.HTTP_201_CREATED)
