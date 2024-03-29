# Generated by Django 2.2.4 on 2019-10-25 15:05

import uuid

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0007_denormalise_created_by")]

    operations = [
        migrations.CreateModel(
            name="CHWRegistration",
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
                ("source", models.CharField(max_length=255)),
                (
                    "id_type",
                    models.CharField(
                        choices=[
                            ("sa_id", "SA ID"),
                            ("passport", "Passport"),
                            ("dob", "Date of birth"),
                        ],
                        max_length=8,
                    ),
                ),
                ("id_number", models.CharField(blank=True, max_length=13)),
                ("passport_country", models.CharField(blank=True, max_length=2)),
                ("passport_number", models.CharField(blank=True, max_length=255)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("language", models.CharField(max_length=3)),
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
