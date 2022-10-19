from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"


urlpatterns = [
    url(
        r"^apitest/",
        views.apitest,
        name="aaq-api-test",
    ),
    url(
        r"^api/v1/inbound/check",
        views.get_first_page,
        name="aaq-get-first-page",
    ),
     url(
        r"^api/v1/inbound/(?P<inbound_id>\d+)/(?P<page_id>\d+)",
        views.get_second_page,
        name="aaq-get-second-page",
    ),
    url(r"^api/v1/", include(router.urls)),
]
