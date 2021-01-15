import codecs
import csv

from django import forms
from django.utils.text import slugify

from eventstore.models import ImportError, MomConnectImport


class MomConnectImportForm(forms.ModelForm):
    file = forms.FileField()

    required_fields = {
        "msisdn",
        "messaging-consent",
        "facility-code",
        "edd-year",
        "edd-month",
        "edd-day",
        "id-type",
    }

    def save(self, commit=True):
        mcimport = super().save(commit=commit)
        try:
            f = codecs.iterdecode(self.cleaned_data["file"].file, "utf-8")
            reader = csv.DictReader(f)
            missing_fields = self.required_fields - set(map(slugify, reader.fieldnames))
            if missing_fields:
                mcimport.status = MomConnectImport.Status.ERROR
                mcimport.save()
                mcimport.errors.create(
                    row_number=0,
                    error_type=ImportError.ErrorType.INVALID_HEADER,
                    error_args=[" ".join(sorted(missing_fields))],
                )
                return mcimport
        except UnicodeDecodeError:
            mcimport.status = MomConnectImport.Status.ERROR
            mcimport.save()
            mcimport.errors.create(
                row_number=0,
                error_type=ImportError.ErrorType.INVALID_FILETYPE,
                error_args=[],
            )
            return mcimport

        return mcimport

    class Meta:
        model = MomConnectImport
        fields = ("file",)
