from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    PositionTracker,
    Registration,
    Source,
    SubscriptionRequest,
    WhatsAppContact,
)
from .tasks import remove_personally_identifiable_fields


class RegistrationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "reg_type",
        "validated",
        "registrant_id",
        "source",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    list_filter = ["source", "validated", "created_at"]
    search_fields = ["registrant_id", "data"]
    actions = ["remove_personal_information"]

    def remove_personal_information(modeladmin, request, queryset):
        for q in queryset.iterator():
            remove_personally_identifiable_fields.delay(str(q.pk))


class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "identity",
        "messageset",
        "next_sequence_number",
        "lang",
        "schedule",
        "created_at",
        "updated_at",
    ]
    list_filter = ["messageset", "created_at"]
    search_fields = ["identity"]


class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ["msisdn", "whatsapp_id", "created"]
    search_fields = ["msisdn"]
    list_filter = ["created"]


admin.site.register(Source)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(SubscriptionRequest, SubscriptionRequestAdmin)
admin.site.register(PositionTracker, SimpleHistoryAdmin)
admin.site.register(WhatsAppContact, WhatsAppContactAdmin)
