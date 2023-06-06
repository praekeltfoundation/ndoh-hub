from django.urls import include, re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"
router.register("mqrbaselinesurvey", views.BaselineSurveyResultViewSet)

urlpatterns = [
    re_path(
        r"^api/v1/mqr_strataarm_validation/",
        views.StrataArmValidationView.as_view(),
        name="mqr_strataarm_validation",
    ),
    re_path(
        r"^api/v1/mqr_randomstrataarm",
        views.RandomStrataArmView.as_view(),
        name="mqr_randomstrataarm",
    ),
    re_path(r"^api/v1/mqr-faq/", views.FaqView.as_view(), name="mqr-faq"),
    re_path(r"^api/v1/mqr-faq-menu/", views.FaqMenuView.as_view(), name="mqr-faq-menu"),
    re_path(
        r"^api/v1/mqr-nextmessage/",
        views.NextMessageView.as_view(),
        name="mqr-nextmessage",
    ),
    re_path(
        r"^api/v1/mqr-midweekarmmessage/",
        views.MidweekArmMessageView.as_view(),
        name="mqr-midweekarmmessage",
    ),
    re_path(
        r"^api/v1/mqr-nextarmmessage/",
        views.NextArmMessageView.as_view(),
        name="mqr-nextarmmessage",
    ),
    re_path(
        r"^api/v1/mqr-firstsenddate",
        views.FirstSendDateView.as_view(),
        name="mqr-firstsenddate",
    ),
    re_path(
        r"^api/v1/mqr-endlinechecks",
        views.MqrEndlineChecksViewSet.as_view(),
        name="mqr-endlinechecks",
    ),
    re_path(r"^api/v1/", include(router.urls)),
]
