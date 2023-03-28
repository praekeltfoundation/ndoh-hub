# Generated by Django 2.2.8 on 2020-05-22 10:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0030_add_covid19_confirmed_contact_fields")]

    operations = [
        migrations.AddIndex(
            model_name="covid19triage",
            index=models.Index(
                fields=["msisdn", "timestamp"], name="eventstore__msisdn_dbf292_idx"
            ),
        )
    ]
