# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-07-28 07:06
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registrations", "0004_auto_20160722_1019"),
    ]

    operations = [
        migrations.CreateModel(
            name="Change",
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
                ("registrant_id", models.CharField(max_length=36)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            (
                                "pmtct_loss_switch",
                                "Change to loss messaging via pmtct app",
                            ),
                            ("pmtct_loss_optout", "Optout due to loss via pmtct app"),
                            (
                                "pmtct_nonloss_optout",
                                "Optout not due to loss via pmtct app",
                            ),
                        ],
                        max_length=255,
                    ),
                ),
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
                        related_name="changes_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="changes",
                        to="registrations.Source",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="changes_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        )
    ]
