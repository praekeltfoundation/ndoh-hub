# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-07-12 20:09
from __future__ import unicode_literals

import uuid

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Registration",
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
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("prebirth", "Mother is pregnant"),
                            ("postbirth", "Baby has been born"),
                            ("loss", "Baby loss"),
                        ],
                        max_length=30,
                    ),
                ),
                ("registrant_id", models.CharField(max_length=36)),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, null=True
                    ),
                ),
                ("validated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registrations_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Source",
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
                ("name", models.CharField(max_length=100)),
                (
                    "authority",
                    models.CharField(
                        choices=[
                            ("patient", "Patient"),
                            ("advisor", "Trusted Advisor"),
                            ("hw_limited", "Health Worker Limited"),
                            ("hw_full", "Health Worker Full"),
                        ],
                        max_length=30,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sources",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SubscriptionRequest",
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
                ("contact", models.CharField(max_length=36)),
                ("messageset", models.IntegerField()),
                ("next_sequence_number", models.IntegerField(default=1)),
                ("lang", models.CharField(max_length=6)),
                ("schedule", models.IntegerField(default=1)),
                (
                    "metadata",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name="registration",
            name="source",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registrations",
                to="registrations.Source",
            ),
        ),
        migrations.AddField(
            model_name="registration",
            name="updated_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registrations_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
