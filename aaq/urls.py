from django.conf.urls import url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"


urlpatterns = [
    url(
        r"^api/v1/inbound/check",
        views.get_first_page,
        name="aaq-get-first-page",
    ),
    url(
        r"^api/v1/inbound/feedback",
        views.add_feedback,
        name="aaq-add-feedback",
    ),
    url(
        r"^api/v1/check-urgency",
        views.check_urgency,
        name="aaq-check-urgency",
    ),
]
