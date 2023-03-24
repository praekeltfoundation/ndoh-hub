# Generated by Django 2.2.4 on 2019-12-24 08:05

import uuid

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0011_add_message_and_event")]

    operations = [
        migrations.CreateModel(
            name="MSISDNSwitch",
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
                ("source", models.CharField(max_length=255)),
                ("old_msisdn", models.CharField(max_length=255)),
                ("new_msisdn", models.CharField(max_length=255)),
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
