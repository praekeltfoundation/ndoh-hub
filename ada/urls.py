from django.urls import include, path

from . import views

urlpatterns = [
    path(
        "confirmredirect/<int:pk>/<str:whatsappid>",
        views.clickActivity,
        name="ada_hook_redirect",
    ),
    path(
        "confirmredirect/<str:pk>/<str:whatsappid>",
        views.clickActivity,
        name="ada_hook_redirect",
    ),
    path("redirect/<int:pk>", views.default_page, name="ada_hook"),
    path("api/v1/ada/", include("rest_framework.urls")),
    path("ada-rest-auth/", include("rest_auth.urls")),
    path("ada-rest-auth/registration/", include("rest_auth.registration.urls")),
    path(
        "api/v2/ada/", views.RapidProStartFlowView.as_view(), name="rapidpro_start_flow"
    ),
]
