from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"


urlpatterns = [
    url(
        r"^api/v1/inbound/check",
        views.AaqFaqViewSet.as_view(),
        name="aaq-inbound-check",
    ),
    url(
        r"^api/v1/inbound/(?P<inbound_id>\d+)/(?P<page_id>\d+)",
        views.PaginatedResponseView.as_view(),
        name="aaq-paginated-check",
    ),
    url(r"^api/v1/", include(router.urls)),
]
