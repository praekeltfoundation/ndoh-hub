# Generated by Django 2.2.13 on 2021-01-15 15:27

import functools

import django.contrib.postgres.fields.jsonb
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import eventstore.validators
import registrations.validators


class Migration(migrations.Migration):

    replaces = [
        ("eventstore", "0038_importerror_importrow_momconnectimport"),
        ("eventstore", "0039_auto_20210114_1424"),
        ("eventstore", "0040_small_integer_fields"),
    ]

    dependencies = [("eventstore", "0037_add_expanded_comorbidities")]

    operations = [
        migrations.CreateModel(
            name="MomConnectImport",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Validating"),
                            (1, "Validated"),
                            (2, "Uploading"),
                            (3, "Complete"),
                            (4, "Error"),
                        ],
                        default=0,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportError",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("row_number", models.PositiveSmallIntegerField()),
                (
                    "error_type",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "File is not a CSV"),
                            (1, "Fields {} not found in header"),
                            (2, "Field {} failed validation: {}"),
                            (3, "Failed validation: {}"),
                        ]
                    ),
                ),
                (
                    "error_args",
                    django.contrib.postgres.fields.jsonb.JSONField(blank=True),
                ),
                (
                    "mcimport",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="errors",
                        to="eventstore.MomConnectImport",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportRow",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("row_number", models.PositiveSmallIntegerField()),
                (
                    "msisdn",
                    models.CharField(
                        max_length=255,
                        validators=[
                            functools.partial(
                                registrations.validators._phone_number,
                                *(),
                                **{"country": "ZA"}
                            )
                        ],
                    ),
                ),
                (
                    "messaging_consent",
                    models.BooleanField(
                        validators=[eventstore.validators.validate_true]
                    ),
                ),
                ("research_consent", models.BooleanField(default=False)),
                ("previous_optout", models.BooleanField(default=False)),
                (
                    "facility_code",
                    models.CharField(
                        max_length=6,
                        validators=[
                            django.core.validators.RegexValidator(
                                "\\d{6}", "Must be 6 digits"
                            )
                        ],
                    ),
                ),
                ("edd_year", models.PositiveSmallIntegerField()),
                ("edd_month", models.PositiveSmallIntegerField()),
                ("edd_day", models.PositiveSmallIntegerField()),
                (
                    "id_type",
                    models.PositiveSmallIntegerField(
                        choices=[(0, "SA ID"), (1, "Passport"), (2, "None")]
                    ),
                ),
                (
                    "id_number",
                    models.CharField(
                        blank=True,
                        max_length=13,
                        validators=[eventstore.validators.validate_sa_id_number],
                    ),
                ),
                (
                    "passport_country",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[
                            (0, "Zimbabwe"),
                            (1, "Mozambique"),
                            (2, "Malawi"),
                            (3, "Nigeria"),
                            (4, "DRC"),
                            (5, "Somalia"),
                            (6, "Other"),
                        ],
                        null=True,
                    ),
                ),
                ("passport_number", models.CharField(blank=True, max_length=255)),
                ("dob_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("dob_month", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("dob_day", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "language",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[
                            (0, "isiZulu"),
                            (1, "isiXhosa"),
                            (2, "Afrikaans"),
                            (3, "English"),
                            (4, "Sesotho sa Leboa"),
                            (5, "Setswana"),
                            (6, "Sesotho"),
                            (7, "Xitsonga"),
                            (8, "SiSwati"),
                            (9, "Tshivenda"),
                            (10, "isiNdebele"),
                        ],
                        default=3,
                    ),
                ),
                (
                    "mcimport",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="eventstore.MomConnectImport",
                    ),
                ),
            ],
        ),
    ]
