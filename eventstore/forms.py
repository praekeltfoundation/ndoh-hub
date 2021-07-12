import codecs
import csv

from django import forms
from django.utils.text import slugify

from eventstore.models import ImportError, ImportRow, MomConnectImport
from eventstore.tasks import validate_momconnect_import


class MomConnectImportForm(forms.ModelForm):
    file = forms.FileField()
    source = forms.CharField(initial="MomConnect Import")

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
            ({"sa_id", "said", "1"}, ImportRow.IDType.SAID),
            ({"passport", "2"}, ImportRow.IDType.PASSPORT),
            ({"none", "dob", "date of birth", "3"}, ImportRow.IDType.NONE),
        )
        t = self.normalise_key(text)
        for keys, value in types:
            if t in keys:
                return value
        return text

    def get_passport_country(self, text):
        types = (
            ({"zimbabwe", "zw", "1"}, ImportRow.PassportCountry.ZW),
            ({"mozambique", "mz", "2"}, ImportRow.PassportCountry.MZ),
            ({"malawi", "mw", "3"}, ImportRow.PassportCountry.MW),
            ({"nigeria", "ng", "4"}, ImportRow.PassportCountry.NG),
            ({"drc", "cd", "5"}, ImportRow.PassportCountry.CD),
            ({"somalia", "so", "6"}, ImportRow.PassportCountry.SO),
            ({"other", "7"}, ImportRow.PassportCountry.OTHER),
        )
        t = self.normalise_key(text)
        for keys, value in types:
            if t in keys:
                return value
        return text

    def get_language(self, text):
        types = (
            ({"isizulu", "zul", "1"}, ImportRow.Language.ZUL),
            ({"isixhosa", "xho"}, ImportRow.Language.XHO),
            ({"afrikaans", "afr"}, ImportRow.Language.AFR),
            ({"english", "eng", "2"}, ImportRow.Language.ENG),
            ({"sesotho_sa_leboa", "nso"}, ImportRow.Language.NSO),
            ({"setswana", "tsn", "3"}, ImportRow.Language.TSN),
            ({"sesotho", "sot"}, ImportRow.Language.SOT),
            ({"xitsonga", "tso"}, ImportRow.Language.TSO),
            ({"siswati", "ssw"}, ImportRow.Language.SSW),
            ({"tshivenda", "ven"}, ImportRow.Language.VEN),
            ({"isindebele", "nbl"}, ImportRow.Language.NBL),
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
        if row_data.get("passport_country"):
            row_data["passport_country"] = self.get_passport_country(
                row_data["passport_country"]
            )
        if row_data.get("language"):
            row_data["language"] = self.get_language(row_data["language"])
        form = ImportRowForm(data=row_data)
        if form.errors:
            mcimport.status = MomConnectImport.Status.ERROR
            mcimport.save()
            for field, errors in form.errors.items():
                for error in errors:
                    if field == "__all__":
                        mcimport.errors.create(
                            row_number=row_number + 2,
                            error_type=ImportError.ErrorType.ROW_VALIDATION_ERROR,
                            error_args=[error],
                        )
                    else:
                        mcimport.errors.create(
                            row_number=row_number + 2,
                            error_type=ImportError.ErrorType.FIELD_VALIDATION_ERROR,
                            error_args=[field, error],
                        )
            return
        form.save()

    def save(self, commit=True):
        mcimport = super().save(commit=commit)
        mcimport.save()
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

        if mcimport.status == MomConnectImport.Status.VALIDATING:
            validate_momconnect_import.delay(mcimport.id)
        return mcimport

    class Meta:
        model = MomConnectImport
        fields = ("file",)


class TextBooleanField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        if not isinstance(value, str):
            return value
        if value.strip().lower() in {"t", "true", "yes", "1"}:
            return True
        if value.strip().lower() in {"f", "false", "no", "0"}:
            return False
        return value


class ImportRowForm(forms.ModelForm):
    messaging_consent = TextBooleanField()
    research_consent = TextBooleanField(required=False, empty_value=False)
    previous_optout = TextBooleanField(required=False, empty_value=True)

    class Meta:
        model = ImportRow
        fields = "__all__"
