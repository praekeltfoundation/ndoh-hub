from django.contrib import admin

from mqr.models import BaselineSurveyResult


@admin.register(BaselineSurveyResult)
class BaselineSurveyResultAdmin(admin.ModelAdmin):
    readonly_fields = ("msisdn", "created_by", "created_at")
    list_display = ("msisdn", "created_at", "airtime_sent")
