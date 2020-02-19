import os

from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path
from django_prometheus import exports as django_prometheus
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.documentation import include_docs_urls

from eventstore.views import (
    BabySwitchViewSet,
    ChannelSwitchViewSet,
    CHWRegistrationViewSet,
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
    EddSwitchViewSet,
    BabyDobSwitchViewSet,
)
from ndoh_hub.decorators import internal_only
from registrations import views

admin.site.site_header = os.environ.get("HUB_TITLE", "NDOH Hub Admin")

v2router = routers.DefaultRouter()
v2router.register("optouts", OptOutViewSet)
v2router.register("babyswitches", BabySwitchViewSet)
v2router.register("channelswitches", ChannelSwitchViewSet)
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
v2router.register("eddeswitches", EddSwitchViewSet)
v2router.register("babydobswitches", BabyDobSwitchViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    url(r"^api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^api/token-auth/", obtain_auth_token),
    url(r"^api/metrics/", views.MetricsView.as_view()),
    url(
        r"^api/health/jembi-facility/",
        views.JembiFacilityCheckHealthcheckView.as_view(),
    ),
    url(r"^api/health/", views.HealthcheckView.as_view()),
    url(r"^docs/", include_docs_urls(title="NDOH Hub")),
    url(r"^", include("registrations.urls")),
    url(r"^", include("changes.urls")),
    path("api/v2/", include(v2router.urls)),
    path(
        "metrics", internal_only(django_prometheus.ExportToDjangoView), name="metrics"
    ),
]
