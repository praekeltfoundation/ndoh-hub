# Generated by Django 2.2.4 on 2019-09-05 13:12

import uuid

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="OptOut",
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
                (
                    "optout_type",
                    models.CharField(
                        choices=[
                            ("stop", "Stop"),
                            ("forget", "Forget"),
                            ("loss", "Loss"),
                        ],
                        max_length=6,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("not_useful", "Not useful"),
                            ("other", "Other"),
                            ("unknown", "Unknown"),
                            ("sms_failure", "SMS failure"),
                            ("miscarriage", "Miscarriage"),
                            ("stillbirth", "Stillbirth"),
                            ("babyloss", "Lost baby"),
                            ("not_hiv_pos", "Not HIV positive"),
                        ],
                        max_length=11,
                    ),
                ),
                ("source", models.CharField(max_length=255)),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        )
    ]
