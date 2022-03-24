from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"
router.register("mqrbaselinesurvey", views.BaselineSurveyResultViewSet)

urlpatterns = [
    url(
        r"^api/v1/mqr_randomstrataarm/",
        views.RandomStrataArmView.as_view(),
        name="mqr_randomstrataarm",
    ),
    url(r"^api/v1/mqr-faq/", views.FaqView.as_view(), name="mqr-faq"),
    url(r"^api/v1/mqr-faq-menu/", views.FaqMenuView.as_view(), name="mqr-faq-menu"),
    url(
        r"^api/v1/mqr-nextmessage/",
        views.NextMessageView.as_view(),
        name="mqr-nextmessage",
    ),
    url(
        r"^api/v1/mqr-firstsenddate",
        views.FirstSendDateView.as_view(),
        name="mqr-firstsenddate",
    ),
    url(r"^api/v1/", include(router.urls)),
]
