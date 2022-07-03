from django.contrib import admin

from .models import (
    AdaSelfAssessment,
    CovidDataLakeEntry,
    RedirectUrl,
    RedirectUrlsEntry,
)

# Register your models here.
admin.site.register(RedirectUrl)
admin.site.register(RedirectUrlsEntry)
admin.site.register(AdaSelfAssessment)
admin.site.register(CovidDataLakeEntry)
