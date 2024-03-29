# Generated by Django 2.2.20 on 2021-05-11 06:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ada", "0011_redirecturl_url")]

    operations = [
        migrations.RenameField(
            model_name="redirecturlsentry", old_name="url", new_name="symptom_check_url"
        ),
        migrations.AlterField(
            model_name="redirecturl",
            name="url",
            field=models.URLField(
                blank=True,
                default="https://hub.momconnect.co.za/confirmredirect",
                max_length=255,
            ),
        ),
    ]
