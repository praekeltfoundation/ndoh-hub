from django import forms
from eventstore.models import MomConnectImport


class MomConnectImportForm(forms.ModelForm):
    file = forms.FileField()

    def save(self, commit=True):
        # TODO: Process file
        return super().save(commit=commit)

    class Meta:
        model = MomConnectImport
        fields = ("file",)
