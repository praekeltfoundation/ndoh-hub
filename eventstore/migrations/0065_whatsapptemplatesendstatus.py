# Generated by Django 4.2.13 on 2024-07-11 09:37

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eventstore", "0064_openhimqueue_timestamp"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppTemplateSendStatus",
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
                ("message_id", models.CharField(blank=True, max_length=255)),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("event_received_at", models.DateTimeField(null=True)),
                ("registration_completed_at", models.DateTimeField(null=True)),
                (
                    "preferred_channel",
                    models.CharField(
                        choices=[("SMS", "SMS"), ("WhatsApp", "WhatsApp")],
                        default="WhatsApp",
                        max_length=8,
                    ),
                ),
            ],
        ),
    ]