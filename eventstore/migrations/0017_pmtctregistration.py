# Generated by Django 2.2.4 on 2020-01-30 08:01

import uuid

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0016_add_fallback_channel_flag")]

    operations = [
        migrations.CreateModel(
            name="PMTCTRegistration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("contact_id", models.UUIDField()),
                ("device_contact_id", models.UUIDField()),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                (
                    "pmtct_risk",
                    models.CharField(
                        choices=[("normal", "Normal"), ("high", "High")], max_length=6
                    ),
                ),
                ("source", models.CharField(max_length=255)),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "created_by",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
            ],
        )
    ]
