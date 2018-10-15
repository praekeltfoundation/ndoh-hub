import os
from django.conf.urls import include, url
from django.urls import path
from django.contrib import admin
from registrations import views
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.documentation import include_docs_urls

admin.site.site_header = os.environ.get('HUB_TITLE',
                                        'NDOH Hub Admin')


urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^api/auth/',
        include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/token-auth/', obtain_auth_token),
    url(r'^api/metrics/', views.MetricsView.as_view()),
    url(r'^api/health/', views.HealthcheckView.as_view()),
    url(r'^docs/', include_docs_urls(title="NDOH Hub")),
    url(r'^', include('registrations.urls')),
    url(r'^', include('changes.urls')),
]
