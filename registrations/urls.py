from django.urls import include, path, re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.trailing_slash = "/?"
router.register(r"contacts", views.WhatsAppContactCheckViewSet)

urlpatterns = [
    path(
        "api/v1/facilityCheck", views.FacilityCheckView.as_view(), name="facility-check"
    ),
    re_path(r"^api/v1/", include(router.urls)),
]
