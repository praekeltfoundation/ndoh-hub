# Generated by Django 2.2.8 on 2020-04-08 13:30

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0028_covid19triage_completed_timestamp")]

    operations = [
        migrations.AlterField(
            model_name="covid19triage",
            name="timestamp",
            field=models.DateTimeField(
                db_index=True, default=django.utils.timezone.now
            ),
        )
    ]
