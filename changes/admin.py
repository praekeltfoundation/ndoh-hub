from django.contrib import admin

from .models import Change
from .tasks import remove_personally_identifiable_fields


class ChangeAdmin(admin.ModelAdmin):
    list_display = ["id", "registrant_id", "action", "validated"]
    list_filter = ["action", "validated"]
    search_fields = ["registrant_id"]
    actions = ["remove_personal_information"]

    def remove_personal_information(modeladmin, request, queryset):
        for q in queryset.iterator():
            remove_personally_identifiable_fields.delay(str(q.pk))


admin.site.register(Change, ChangeAdmin)
