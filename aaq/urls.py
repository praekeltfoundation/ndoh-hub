from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"


urlpatterns = [
    re_path(
        r"^api/v1/inbound/check",
        views.get_first_page,
        name="aaq-get-first-page",
    ),
    re_path(
        r"^api/v1/inbound/feedback",
        views.add_feedback,
        name="aaq-add-feedback",
    ),
    re_path(
        r"^api/v1/check-urgency",
        views.check_urgency,
        name="aaq-check-urgency",
    ),
    re_path(
        r"^api/v2/response-feedback",
        views.response_feedback,
        name="aaq-response-feedback",
    ),
    re_path(
        r"^api/v2/content-feedback",
        views.content_feedback,
        name="aaq-content-feedback",
    ),
    re_path(
        r"^api/v2/search",
        views.search,
        name="aaq-search",
    ),
]
