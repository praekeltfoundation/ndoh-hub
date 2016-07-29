from django.contrib import admin

from .models import Change


class ChangeAdmin(admin.ModelAdmin):
    list_display = [
        "id", "registrant_id", "action", "validated"]
    list_filter = ["action", "validated"]
    search_fields = ["registrant_id"]


admin.site.register(Change, ChangeAdmin)
