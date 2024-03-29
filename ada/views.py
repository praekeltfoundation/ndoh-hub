import json
import re
import urllib.parse
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import HttpResponseRedirect, render
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from ada.serializers import (
    AdaChoiceTypeSerializer,
    AdaInputTypeSerializer,
    AdaTextTypeSerializer,
    StartAssessmentSerializer,
    SubmitCastorDataSerializer,
    SymptomCheckSerializer,
)

from .models import (
    AdaSelfAssessment,
    CovidDataLakeEntry,
    RedirectUrl,
    RedirectUrlsEntry,
)
from .tasks import post_to_topup_endpoint, start_prototype_survey_flow, start_topup_flow
from .utils import (
    abort_assessment,
    build_rp_request,
    create_castor_record,
    encodeurl,
    format_message,
    get_edc_report,
    get_endpoint,
    get_path,
    get_report,
    get_step,
    pdf_endpoint,
    pdf_ready,
    post_to_ada,
    post_to_ada_start_assessment,
    previous_question,
    submit_castor_data,
    upload_edc_media,
    upload_turn_media,
)


class RapidProStartFlowView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = SymptomCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        whatsappid = serializer.validated_data.get("whatsappid")
        match = re.match(
            (
                r"^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]"
                r"*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$"
            ),
            whatsappid,
        )
        if match:
            start_prototype_survey_flow.delay(str(whatsappid))

        return Response({}, status=status.HTTP_200_OK)


class RapidProStartTopupFlowView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = SymptomCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        whatsappid = serializer.validated_data.get("whatsappid")

        start_topup_flow.delay(str(whatsappid))

        return Response({}, status=status.HTTP_200_OK)


def clickActivity(request: HttpRequest, pk: int, whatsappid: str) -> HttpResponse:
    try:
        redirect_url = RedirectUrl.objects.get(id=pk)
    except (ValueError, RedirectUrl.DoesNotExist):
        raise Http404()
    else:
        store_url_entry = RedirectUrlsEntry(symptom_check_url=redirect_url)
        store_url_entry.save()
        customization_id = settings.ADA_CUSTOMIZATION_ID
        url = f"{redirect_url.symptom_check_url}"
        qs = urlencode({"whatsappid": whatsappid, "customizationId": customization_id})
        destination_url = f"{url}?{qs}"
        return HttpResponseRedirect(destination_url)


def default_page(request: HttpRequest, pk: int) -> HttpResponse:
    whatsappid = request.GET.get("whatsappid")
    if whatsappid is None:
        return render(
            request, "index.html", {"error": "404 Bad Request: Whatsappid is none"}
        )
    else:
        context = {"pk": pk, "whatsappid": whatsappid}
        return render(request, "meta_refresh.html", context)


def topuprequest(request: HttpRequest) -> HttpResponse:
    whatsappid = request.GET.get("whatsappid")
    if whatsappid is None:
        return render(
            request, "index.html", {"error": "404 Bad Request: Whatsappid is none"}
        )
    else:
        context = {"whatsappid": whatsappid}
        post_to_topup_endpoint(str(whatsappid))
        return render(request, "topup_request.html", context)


class Covid(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        body = request.data
        resource_id = body["id"]
        store_url_entry = CovidDataLakeEntry(resource_id=resource_id, data=body)
        store_url_entry.save()
        return Response({}, status=status.HTTP_200_OK)


class PresentationLayerView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        body = request.data
        cardType = body["cardType"]
        if cardType == "CHOICE":
            serializer = AdaChoiceTypeSerializer(body)
        elif cardType == "TEXT":
            serializer = AdaTextTypeSerializer(body)
        elif cardType == "INPUT":
            serializer = AdaInputTypeSerializer(body)
        else:
            serializer = StartAssessmentSerializer(body)
        validated_body = serializer.validate_value(body)
        url = get_endpoint(validated_body)
        reverse_url = encodeurl(body, url)
        return HttpResponseRedirect(reverse_url)


class StartAssessment(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        result = request.GET
        data = result.dict()
        contact_uuid = data["contact_uuid"]
        request = build_rp_request(data)
        response = post_to_ada_start_assessment(request, contact_uuid)
        path = get_path(response)
        step = get_step(response)
        data["path"] = path
        data["step"] = step
        request = build_rp_request(data)
        ada_response = post_to_ada(request, path, contact_uuid)
        message = format_message(ada_response)
        return Response(message, status=status.HTTP_200_OK)


class NextDialog(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        result = request.GET
        data = result.dict()
        contact_uuid = data["contact_uuid"]
        step = data["step"]
        value = data["value"]
        description = data["description"]
        title = data["title"]
        msisdn = data["msisdn"]
        choiceContext = data["choiceContext"]
        choiceContext = str(choiceContext)[1:-1]
        choiceContext = choiceContext.replace("'", "")
        choiceContext = list(choiceContext.split(","))
        choiceContext = [i.lstrip() for i in choiceContext]
        roadblock = ""

        if data["cardType"] == "CHOICE":
            optionId = int(value) - 1
            choiceContext = choiceContext[optionId]
        else:
            optionId = data["optionId"]
        path = get_path(data)
        assessment_id = path.split("/")[-3]
        request = build_rp_request(data)
        ada_response = post_to_ada(request, path, contact_uuid)
        if ada_response == 410:
            return Response("Timeout", status=status.HTTP_410_GONE)
        pdf = pdf_ready(ada_response)
        if pdf:
            report_path = ada_response["_links"]["report"]["href"]
            pdf_content = get_report(report_path, contact_uuid)
            pdf_media_id = upload_turn_media(pdf_content)
        else:
            pdf_media_id = ""
            if ada_response["cardType"] == "ROADBLOCK":
                roadblock = "ROADBLOCK"
        if data["cardType"] != "TEXT" or pdf_media_id != "":
            if data["cardType"] == "INPUT":
                optionId = None
            if pdf_media_id != "":
                optionId = None
            store_url_entry = AdaSelfAssessment(
                contact_id=contact_uuid,
                msisdn=msisdn,
                assessment_id=assessment_id,
                title=title,
                description=description,
                step=step,
                user_input=value,
                optionId=optionId,
                choice=choiceContext,
                pdf_media_id=pdf_media_id,
                roadblock=roadblock,
            )
            store_url_entry.save()
        if not pdf:
            message = format_message(ada_response)
            return Response(message, status=status.HTTP_200_OK)
        else:
            ada_response["pdf_media_id"] = pdf_media_id
            response = pdf_endpoint(ada_response)
            return HttpResponseRedirect(response)


class PreviousDialog(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        result = request.GET
        data = result.dict()
        contact_uuid = data["contact_uuid"]
        path = get_path(data)
        request = build_rp_request(data)
        ada_response = previous_question(request, path, contact_uuid)
        message = format_message(ada_response)
        return Response(message, status=status.HTTP_200_OK)


class Abort(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        result = request.GET
        data = result.dict()
        response = abort_assessment(data)
        return Response(response, status=status.HTTP_200_OK)


class Reports(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        payload = request.GET.get("payload")
        urldecoded = urllib.parse.unquote(payload)
        data = json.loads(urldecoded)
        message = format_message(data)
        return Response(message, status=status.HTTP_200_OK)


class SubmitCastorData(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = SubmitCastorDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        records = serializer.validated_data["records"]
        record_id = serializer.validated_data.get("edc_record_id")
        if not record_id:
            record_id = create_castor_record(token)

        for record in records:
            submit_castor_data(token, record_id, record["id"], record["value"])

        return Response({"record_id": record_id}, status=status.HTTP_200_OK)


class EDC_Reports(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        body = request.data
        contact_uuid = body["contact_uuid"]
        report_id = body["report_id"]
        study_id = body["study_id"]
        record_id = body["record_id"]
        field_id = body["field_id"]
        token = body["token"]
        pdf_content = get_edc_report(report_id, contact_uuid)
        upload_edc_media(pdf_content, study_id, record_id, field_id, token)
        return Response("Successfully submitted to Castor", status=status.HTTP_200_OK)
