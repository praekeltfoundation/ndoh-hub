from django.contrib import admin

from .models import AdaSelfAssessment, RedirectUrl, RedirectUrlsEntry

# Register your models here.
admin.site.register(RedirectUrl)
admin.site.register(RedirectUrlsEntry)
admin.site.register(AdaSelfAssessment)
