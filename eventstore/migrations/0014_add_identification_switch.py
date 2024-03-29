# Generated by Django 2.2.4 on 2020-01-06 13:47

import uuid

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0013_add_language_switch")]

    operations = [
        migrations.CreateModel(
            name="IdentificationSwitch",
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
                (
                    "old_identification_type",
                    models.CharField(
                        choices=[
                            ("sa_id", "SA ID"),
                            ("passport", "Passport"),
                            ("dob", "Date of birth"),
                        ],
                        max_length=8,
                    ),
                ),
                (
                    "new_identification_type",
                    models.CharField(
                        choices=[
                            ("sa_id", "SA ID"),
                            ("passport", "Passport"),
                            ("dob", "Date of birth"),
                        ],
                        max_length=8,
                    ),
                ),
                (
                    "old_id_number",
                    models.CharField(blank=True, default="", max_length=13),
                ),
                (
                    "new_id_number",
                    models.CharField(blank=True, default="", max_length=13),
                ),
                ("old_dob", models.DateField(blank=True, default=None, null=True)),
                ("new_dob", models.DateField(blank=True, default=None, null=True)),
                (
                    "old_passport_country",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("zw", "Zimbabwe"),
                            ("mz", "Mozambique"),
                            ("mw", "Malawi"),
                            ("ng", "Nigeria"),
                            ("cd", "DRC"),
                            ("so", "Somalia"),
                            ("other", "Other"),
                        ],
                        default="",
                        max_length=5,
                    ),
                ),
                (
                    "new_passport_country",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("zw", "Zimbabwe"),
                            ("mz", "Mozambique"),
                            ("mw", "Malawi"),
                            ("ng", "Nigeria"),
                            ("cd", "DRC"),
                            ("so", "Somalia"),
                            ("other", "Other"),
                        ],
                        default="",
                        max_length=5,
                    ),
                ),
                (
                    "old_passport_number",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "new_passport_number",
                    models.CharField(blank=True, default="", max_length=255),
                ),
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
