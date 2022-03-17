from django.urls import path

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
    path(
        "api/v2/ada/", views.RapidProStartFlowView.as_view(), name="rapidpro_start_flow"
    ),
    path("topuprequest/", views.topuprequest, name="topuprequest_hook"),
    path(
        "api/v2/ada/topup/",
        views.RapidProStartTopupFlowView.as_view(),
        name="rapidpro_topup_flow",
    ),
    path(
        "api/v2/ada/startassessment",
        views.PresentationLayerView.as_view(),
        name="ada-start-assessment",
    ),
]
