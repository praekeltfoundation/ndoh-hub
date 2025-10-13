from django.urls import path

from . import views

# fmt: off
urlpatterns = [
    path(
        "label/feedback/",
        views.LabelFeedbackView.as_view(),
        name="label_feedback"
    ),
]
