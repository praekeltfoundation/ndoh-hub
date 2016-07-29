from django.conf.urls import url
from . import views


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r'^api/v1/change/', views.ChangePost.as_view()),
]
