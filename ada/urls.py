from django.urls import path

from . import views

urlpatterns = [
    path("confirmredirect/<int:pk>", views.clickActivity, name="ada_hook_redirect"),
    path("redirect/<int:pk>", views.default_page, name="ada_hook"),
]
