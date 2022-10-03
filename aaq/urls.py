from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"


urlpatterns = [
    url(
        r"^api/v1/aaq-faq",
        views.AaqFaqViewSet.as_view(),
        name="aaq-get-faqs",
    ),
    url(r"^api/v1/", include(router.urls)),
]
