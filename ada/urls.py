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
        "api/v2/ada/assessments",
        views.PresentationLayerView.as_view(),
        name="ada-assessments",
    ),
    path(
        "api/v2/ada/startassessment",
        views.StartAssessment.as_view(),
        name="ada-start-assessment",
    ),
    path("api/v2/ada/nextdialog", views.NextDialog.as_view(), name="ada-next-dialog"),
    path(
        "api/v2/ada/previousdialog",
        views.PreviousDialog.as_view(),
        name="ada-previous-dialog",
    ),
    path("api/v2/ada/reports", views.Reports.as_view(), name="ada-reports"),
    path("api/v2/ada/abort", views.Abort.as_view(), name="ada-abort"),
    path("api/v2/ada/covid", views.Covid.as_view(), name="ada-covid"),
    path("api/v2/ada/edc_reports", views.EDC_Reports.as_view(), name="ada-edc-reports"),
    path(
        "api/v2/ada/submit_castor_data",
        views.SubmitCastorData.as_view(),
        name="submit-castor-data",
    ),
]
