from django.contrib import admin
from .models import RedirectUrl, RedirectUrlsEntry

# Register your models here.
admin.site.register(RedirectUrl)
admin.site.register(RedirectUrlsEntry)
