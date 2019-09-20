# Generated by Django 2.2.4 on 2019-09-19 12:58

import uuid

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("eventstore", "0003_create_channelswitch"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicRegistration",
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
                    "language",
                    models.CharField(
                        choices=[
                            ("afr", "Afrikaans"),
                            ("eng", "English"),
                            ("nbl", "isiNdebele"),
                            ("nso", "Sepedi"),
                            ("sot", "Sesotho"),
                            ("ssw", "Siswati"),
                            ("tsn", "Setswana"),
                            ("tso", "Xitsonga"),
                            ("ven", "Tshivenda"),
                            ("xho", "isiXhosa"),
                            ("zul", "isiZulu"),
                        ],
                        max_length=3,
                    ),
                ),
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
