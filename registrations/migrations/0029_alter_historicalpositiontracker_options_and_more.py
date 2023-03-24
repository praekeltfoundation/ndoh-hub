# Generated by Django 4.1 on 2023-03-24 13:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registrations", "0028_auto_20210121_1406"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="historicalpositiontracker",
            options={
                "get_latest_by": ("history_date", "history_id"),
                "ordering": ("-history_date", "-history_id"),
                "verbose_name": "historical position tracker",
                "verbose_name_plural": "historical position trackers",
            },
        ),
        migrations.AlterField(
            model_name="historicalpositiontracker",
            name="history_date",
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterField(
            model_name="jembisubmission",
            name="request_data",
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name="jembisubmission",
            name="response_headers",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="registration",
            name="data",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="subscriptionrequest",
            name="metadata",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
