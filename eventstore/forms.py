import codecs
import csv

from django import forms
from django.forms.models import ModelForm
from django.utils.text import slugify

from eventstore.models import ImportError, ImportRow, MomConnectImport


class MomConnectImportForm(forms.ModelForm):
    file = forms.FileField()

    required_fields = {
        "msisdn",
        "messaging_consent",
        "facility_code",
        "edd_year",
        "edd_month",
        "edd_day",
        "id_type",
    }

    def normalise_key(self, text):
        """
        Returns keys/headers in snake case
        """
        text = text or ""
        return slugify(text).replace("-", "_")

    def get_id_type(self, text):
        types = (
            ({"sa_id", "said"}, ImportRow.IDType.SAID),
            ({"passport"}, ImportRow.IDType.PASSPORT),
            ({"none", "dob", "date of birth"}, ImportRow.IDType.NONE),
        )
        t = self.normalise_key(text)
        for keys, value in types:
            if t in keys:
                return value
        return text

    def create_row(self, mcimport, row_number, row_data):
        row_data = {self.normalise_key(k): v for k, v in row_data.items()}
        row_data["mcimport"] = mcimport.pk
        row_data["row_number"] = row_number + 2  # First row is header
        row_data["id_type"] = self.get_id_type(row_data["id_type"])
        form = ImportRowForm(data=row_data)
        if form.errors:
            mcimport.status = MomConnectImport.Status.ERROR
            mcimport.save()
            for field, errors in form.errors.items():
                for error in errors:
                    mcimport.errors.create(
                        row_number=row_number + 2,
                        error_type=ImportError.ErrorType.VALIDATION_ERROR,
                        error_args=[field, error],
                    )
            return
        form.save()

    def save(self, commit=True):
        mcimport = super().save(commit=commit)
        try:
            f = codecs.iterdecode(self.cleaned_data["file"].file, "utf-8")
            reader = csv.DictReader(f)
            missing_fields = self.required_fields - set(
                map(self.normalise_key, reader.fieldnames)
            )
            if missing_fields:
                mcimport.status = MomConnectImport.Status.ERROR
                mcimport.save()
                mcimport.errors.create(
                    row_number=1,
                    error_type=ImportError.ErrorType.INVALID_HEADER,
                    error_args=[" ".join(sorted(missing_fields))],
                )
                return mcimport
            for i, row in enumerate(reader):
                self.create_row(mcimport, i, row)
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


class ImportRowForm(forms.ModelForm):
    class Meta:
        model = ImportRow
        fields = "__all__"
