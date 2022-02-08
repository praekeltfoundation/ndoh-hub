# Generated by Django 2.2.24 on 2021-12-07 06:26

import uuid

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("eventstore", "0049_auto_20211202_1220")]

    operations = [
        migrations.CreateModel(
            name="AskFeedback",
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
                ("question_answered", models.BooleanField(default=False)),
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