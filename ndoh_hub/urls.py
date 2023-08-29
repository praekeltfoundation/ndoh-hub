import os

from django.contrib import admin
from django.urls import include, path, re_path
from django_prometheus import exports as django_prometheus
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.documentation import include_docs_urls

from eventstore.views import (
    AdaAssessmentNotificationViewSet,
    BabyDobSwitchViewSet,
    BabySwitchViewSet,
    CDUAddressUpdateViewSet,
    ChannelSwitchViewSet,
    CHWRegistrationViewSet,
    Covid19TriageStartViewSet,
    Covid19TriageV2ViewSet,
    Covid19TriageV3ViewSet,
    Covid19TriageV4ViewSet,
    Covid19TriageViewSet,
    DBEOnBehalfOfProfileViewSet,
    DeliveryFailureViewSet,
    EddSwitchViewSet,
    FeedbackViewSet,
    ForgetContactView,
    HCSStudyBRandomizationViewSet,
    HealthCheckUserProfileViewSet,
    IdentificationSwitchViewSet,
    LanguageSwitchViewSet,
    MessagesViewSet,
    MSISDNSwitchViewSet,
    OptOutViewSet,
    PMTCTRegistrationViewSet,
    PostbirthRegistrationViewSet,
    PrebirthRegistrationViewSet,
    PublicRegistrationViewSet,
    ResearchOptinSwitchViewSet,
    WhatsAppEventsViewSet,
)
from ndoh_hub.decorators import internal_only

from . import views

admin.site.site_header = os.environ.get("HUB_TITLE", "NDOH Hub Admin")

v2router = routers.DefaultRouter()
v2router.register("optouts", OptOutViewSet)
v2router.register("babyswitches", BabySwitchViewSet)
v2router.register("channelswitches", ChannelSwitchViewSet)
v2router.register("covid19triage", Covid19TriageViewSet)
v2router.register("covid19triagestart", Covid19TriageStartViewSet)
v2router.register("hcsstudybrandomarm", HCSStudyBRandomizationViewSet)
v2router.register("msisdnswitches", MSISDNSwitchViewSet)
v2router.register("languageswitches", LanguageSwitchViewSet)
v2router.register("identificationswitches", IdentificationSwitchViewSet)
v2router.register("chwregistrations", CHWRegistrationViewSet)
v2router.register("publicregistrations", PublicRegistrationViewSet)
v2router.register("prebirthregistrations", PrebirthRegistrationViewSet)
v2router.register("pmtctregistrations", PMTCTRegistrationViewSet)
v2router.register("postbirthregistrations", PostbirthRegistrationViewSet)
v2router.register("researchoptins", ResearchOptinSwitchViewSet)
v2router.register("messages", MessagesViewSet, basename="messages")
v2router.register("eddswitches", EddSwitchViewSet)
v2router.register("babydobswitches", BabyDobSwitchViewSet)
v2router.register("feedback", FeedbackViewSet)
v2router.register("cduaddressupdate", CDUAddressUpdateViewSet)
v2router.register("healthcheckuserprofile", HealthCheckUserProfileViewSet)
v2router.register("dbeonbehalfofprofile", DBEOnBehalfOfProfileViewSet)
v2router.register(
    "adaassessmentnotification",
    AdaAssessmentNotificationViewSet,
    basename="adaassessmentnotification",
)
v2router.register("deliveryfailure", DeliveryFailureViewSet)
v2router.register("events", WhatsAppEventsViewSet)

v3router = routers.DefaultRouter()
v3router.register("covid19triage", Covid19TriageV2ViewSet, basename="covid19triagev2")

v4router = routers.DefaultRouter()
v4router.register("covid19triage", Covid19TriageV3ViewSet, basename="covid19triagev3")

v5router = routers.DefaultRouter()
v5router.register("covid19triage", Covid19TriageV4ViewSet, basename="covid19triagev4")

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(r"^api/token-auth/", obtain_auth_token),
    re_path(r"^docs/", include_docs_urls(title="NDOH Hub")),
    re_path(r"^", include("mqr.urls")),
    re_path(r"^", include("aaq.urls")),
    re_path(r"^", include("registrations.urls")),
    path("", include("ada.urls")),
    re_path(
        r"^api/v1/forgetcontact/", ForgetContactView.as_view(), name="forgetcontact"
    ),
    path("api/v2/", include(v2router.urls)),
    path("api/v3/", include(v3router.urls)),
    path("api/v4/", include(v4router.urls)),
    path("api/v5/", include(v5router.urls)),
    path(
        "metrics", internal_only(django_prometheus.ExportToDjangoView), name="metrics"
    ),
    re_path(
        r"^api/v1/sendwhatsapptemplate",
        views.SendWhatsappTemplateView.as_view(),
        name="send-whatsapp-template",
    ),
]
