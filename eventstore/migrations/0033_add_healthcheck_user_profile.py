# Generated by Django 2.2.8 on 2020-08-05 09:22

import functools

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models

import eventstore.validators


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0032_deliveryfailure_timestamp")]

    operations = [
        migrations.CreateModel(
            name="HealthCheckUserProfile",
            fields=[
                (
                    "msisdn",
                    models.CharField(
                        max_length=255,
                        primary_key=True,
                        serialize=False,
                        validators=[
                            functools.partial(
                                eventstore.validators._phone_number,
                                *(),
                                **{"country": "ZA"}
                            )
                        ],
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, default=None, max_length=255, null=True
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, default=None, max_length=255, null=True
                    ),
                ),
                (
                    "province",
                    models.CharField(
                        choices=[
                            ("ZA-EC", "Eastern Cape"),
                            ("ZA-FS", "Free State"),
                            ("ZA-GT", "Gauteng"),
                            ("ZA-LP", "Limpopo"),
                            ("ZA-MP", "Mpumalanga"),
                            ("ZA-NC", "Northern Cape"),
                            ("ZA-NL", "Kwazulu-Natal"),
                            ("ZA-NW", "North-West (South Africa)"),
                            ("ZA-WC", "Western Cape"),
                        ],
                        max_length=6,
                    ),
                ),
                ("city", models.CharField(max_length=255)),
                (
                    "age",
                    models.CharField(
                        choices=[
                            ("<18", "<18"),
                            ("18-40", "18-40"),
                            ("40-65", "40-65"),
                            (">65", ">65"),
                        ],
                        max_length=5,
                    ),
                ),
                (
                    "date_of_birth",
                    models.DateField(blank=True, default=None, null=True),
                ),
                (
                    "gender",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("male", "Male"),
                            ("female", "Female"),
                            ("other", "Other"),
                            ("not_say", "Rather not say"),
                        ],
                        default="",
                        max_length=7,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        validators=[eventstore.validators.geographic_coordinate],
                    ),
                ),
                (
                    "city_location",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=255,
                        null=True,
                        validators=[eventstore.validators.geographic_coordinate],
                    ),
                ),
                (
                    "preexisting_condition",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("yes", "Yes"),
                            ("no", "No"),
                            ("not_sure", "Not sure"),
                        ],
                        default="",
                        max_length=9,
                    ),
                ),
                (
                    "rooms_in_household",
                    models.IntegerField(blank=True, default=None, null=True),
                ),
                (
                    "persons_in_household",
                    models.IntegerField(blank=True, default=None, null=True),
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
