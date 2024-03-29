# Generated by Django 2.2.4 on 2019-11-19 15:23

import django.contrib.postgres.fields.jsonb
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0010_add_external_registration_id")]

    operations = [
        migrations.CreateModel(
            name="Event",
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
                ("message_id", models.CharField(blank=True, max_length=255)),
                ("recipient_id", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(blank=True, max_length=255)),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_by", models.CharField(blank=True, max_length=255)),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.CharField(
                        blank=True, max_length=255, primary_key=True, serialize=False
                    ),
                ),
                ("contact_id", models.CharField(blank=True, max_length=255)),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("type", models.CharField(blank=True, max_length=255)),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
                (
                    "message_direction",
                    models.CharField(
                        choices=[("I", "Inbound"), ("O", "Outbound")], max_length=1
                    ),
                ),
                ("created_by", models.CharField(blank=True, max_length=255)),
            ],
        ),
    ]
