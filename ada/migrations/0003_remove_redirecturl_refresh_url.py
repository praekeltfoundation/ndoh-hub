# Generated by Django 2.2.20 on 2021-05-05 09:42

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("ada", "0002_auto_20210505_0815")]

    operations = [migrations.RemoveField(model_name="redirecturl", name="refresh_url")]
