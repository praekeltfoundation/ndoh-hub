from django.contrib import admin

from registrations.models import Registration


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


admin.site.register(Registration, RegistrationAdmin)
