from django.conf.urls import include, url
from django.urls import path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
# Make trailing slash optional
router.trailing_slash = "/?"
router.register(r"user", views.UserViewSet)
router.register(r"group", views.GroupViewSet)
router.register(r"source", views.SourceViewSet)
router.register(r"webhook", views.HookViewSet)
router.register(r"registrations", views.RegistrationGetViewSet)
router.register(r"position_tracker", views.PositionTrackerViewset)
router.register(r"contacts", views.WhatsAppContactCheckViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r"^api/v1/registration/", views.RegistrationPost.as_view()),
    url(
        r"^api/v1/extregistration/",
        views.ThirdPartyRegistration.as_view(),
        name="external-registration",
    ),
    url(r"^api/v1/jembiregistration/$", views.JembiAppRegistration.as_view()),
    url(
        r"^api/v1/jembiregistration/(?P<registration_id>[^/]+)/$",
        views.JembiAppRegistrationStatus.as_view(),
    ),
    url(
        r"^api/v1/jembi/helpdesk/outgoing/$",
        views.JembiHelpdeskOutgoingView.as_view(),
        name="jembi-helpdesk-outgoing",
    ),
    url(
        r"^api/v1/facilitycode_check/",
        views.FacilityCodeCheckView.as_view(),
        name="facilitycode-check",
    ),
    url(r"^api/v1/user/token/$", views.UserView.as_view(), name="create-user-token"),
    path(
        "api/v1/engage/context",
        views.EngageContextView.as_view(),
        name="engage-context",
    ),
    path(
        "api/v1/engage/action", views.EngageActionView.as_view(), name="engage-action"
    ),
    path(
        "api/v1/subscription_check/",
        views.SubscriptionCheckView.as_view(),
        name="subscription-check",
    ),
    path(
        "api/v1/rapidpro/clinic_registration",
        views.RapidProClinicRegistrationView.as_view(),
        name="rapidpro-clinic-registration",
    ),
    path(
        "api/v1/rapidpro/public_registration",
        views.RapidProPublicRegistrationView.as_view(),
        name="rapidpro-public-registration",
    ),
    url(r"^api/v1/", include(router.urls)),
]
