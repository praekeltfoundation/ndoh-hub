from django.contrib import admin
from django.core.paginator import Paginator
from django.db import OperationalError, connection, transaction
from django.utils.functional import cached_property

from eventstore.forms import MomConnectImportForm
from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    Covid19TriageStart,
    DeliveryFailure,
    EddSwitch,
    IdentificationSwitch,
    ImportError,
    ImportRow,
    LanguageSwitch,
    MomConnectImport,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)


class ApproximatePaginator(Paginator):
    """
    Paginator that returns an approximate count if doing the real count takes too long
    A mix between:
    https://hakibenita.com/optimizing-the-django-admin-paginator
    https://wiki.postgresql.org/wiki/Count_estimate
    """

    @cached_property
    def count(self):
        cursor = connection.cursor()
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout TO 50")
            try:
                return super().count
            except OperationalError:
                pass
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT reltuples FROM pg_class WHERE relname = %s",
                [self.object_list.query.model._meta.db_table],
            )
            return int(cursor.fetchone()[0])


class BaseEventAdmin(admin.ModelAdmin):
    sortable_by = ()
    paginator = ApproximatePaginator
    show_full_result_count = False

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user.username
        super().save_model(request, obj, form, change)


@admin.register(OptOut)
class OptOutAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "optout_type", "reason", "source", "timestamp")


@admin.register(BabySwitch)
class BabySwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(ChannelSwitch)
class ChannelSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(MSISDNSwitch)
class MSISDNSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(LanguageSwitch)
class LanguageSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(IdentificationSwitch)
class IdentificationSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(ResearchOptinSwitch)
class ResearchOptinSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(PublicRegistration)
class PublicRegistrationAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(PrebirthRegistration)
class PrebirthRegistrationAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "edd", "facility_code", "timestamp")


@admin.register(PostbirthRegistration)
class PostbirthRegistrationAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "baby_dob", "facility_code", "timestamp")


@admin.register(CHWRegistration)
class CHWRegistrationAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(DeliveryFailure)
class DeliveryFailureAdmin(BaseEventAdmin):
    readonly_fields = ("contact_id", "number_of_failures")
    list_display = ("contact_id", "number_of_failures")


@admin.register(PMTCTRegistration)
class PMTCTRegistrationAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "date_of_birth", "pmtct_risk", "timestamp")


@admin.register(EddSwitch)
class EddSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(BabyDobSwitch)
class BabyDobSwitchAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("contact_id", "source", "timestamp")


@admin.register(Covid19Triage)
class Covid19TriageAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("msisdn", "risk", "source", "timestamp")


@admin.register(Covid19TriageStart)
class Covid19TriageStartAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("msisdn", "source", "timestamp")


@admin.register(CDUAddressUpdate)
class CDUAddressUpdateAdmin(BaseEventAdmin):
    readonly_fields = ("id", "created_by", "timestamp")
    list_display = ("last_name", "folder_number", "timestamp")


class ImportErrorInline(admin.TabularInline):
    model = ImportError
    fields = ("row_number", "error")
    readonly_fields = ("row_number", "error")

    # Don't allow any changes
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ImportRowInline(admin.TabularInline):
    model = ImportRow

    # Don't allow any changes
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MomConnectImport)
class MomConnectImportAdmin(admin.ModelAdmin):
    readonly_fields = ("timestamp", "status")
    list_display = ("timestamp", "status")
    inlines = (ImportErrorInline, ImportRowInline)
    form = MomConnectImportForm

    def get_inline_instances(self, request, obj=None):
        # Hide inline for creating new import
        if obj is None:
            return ()
        return super().get_inline_instances(request, obj)

    def get_readonly_fields(self, request, obj=None):
        # Hide readonly fields when creating new import
        if obj is None:
            return ()
        return super().get_readonly_fields(request, obj)
