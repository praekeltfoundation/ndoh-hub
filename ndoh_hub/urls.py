import os

from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path
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
    EddSwitchViewSet,
    FeedbackViewSet,
    ForgetContactView,
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
)
from mqr.views import RandomArmView, RandomStrataArmView
from ndoh_hub.decorators import internal_only

admin.site.site_header = os.environ.get("HUB_TITLE", "NDOH Hub Admin")

v2router = routers.DefaultRouter()
v2router.register("optouts", OptOutViewSet)
v2router.register("babyswitches", BabySwitchViewSet)
v2router.register("channelswitches", ChannelSwitchViewSet)
v2router.register("covid19triage", Covid19TriageViewSet)
v2router.register("covid19triagestart", Covid19TriageStartViewSet)
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

v3router = routers.DefaultRouter()
v3router.register("covid19triage", Covid19TriageV2ViewSet, basename="covid19triagev2")

v4router = routers.DefaultRouter()
v4router.register("covid19triage", Covid19TriageV3ViewSet, basename="covid19triagev3")

v5router = routers.DefaultRouter()
v5router.register("covid19triage", Covid19TriageV4ViewSet, basename="covid19triagev4")

urlpatterns = [
    path("admin/", admin.site.urls),
    url(r"^api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^api/token-auth/", obtain_auth_token),
    url(r"^docs/", include_docs_urls(title="NDOH Hub")),
    url(r"^", include("registrations.urls")),
    path("", include("ada.urls")),
    url(r"^api/v1/forgetcontact/", ForgetContactView.as_view(), name="forgetcontact"),
    url(r"^api/v1/mqr_randomarm/", RandomArmView.as_view(), name="mqr-randomarm"),
    url(r"^api/v1/mqr_randomstrataarm/", RandomStrataArmView.as_view(),
        name="mqr_randomstrataarm"),
    path("api/v2/", include(v2router.urls)),
    path("api/v3/", include(v3router.urls)),
    path("api/v4/", include(v4router.urls)),
    path("api/v5/", include(v5router.urls)),
    path(
        "metrics", internal_only(django_prometheus.ExportToDjangoView), name="metrics"
    ),
]
