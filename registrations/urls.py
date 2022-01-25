from django.urls import path

from . import views

urlpatterns = [
    path(
        "api/v1/facilityCheck", views.FacilityCheckView.as_view(), name="facility-check"
    ),
]
