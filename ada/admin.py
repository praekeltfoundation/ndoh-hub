from django.contrib import admin

from .models import AdaSymptomAssessment, RedirectUrl, RedirectUrlsEntry

# Register your models here.
admin.site.register(RedirectUrl)
admin.site.register(RedirectUrlsEntry)
admin.site.register(AdaSymptomAssessment)
