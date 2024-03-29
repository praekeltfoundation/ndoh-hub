# Generated by Django 4.1 on 2023-04-04 14:12

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("eventstore", "0055_alter_publicregistration_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="recipient_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="event",
                    name="recipient_id",
                    field=models.CharField(blank=True, db_index=True, max_length=255),
                ),
            ],
            database_operations=[
                AddIndexConcurrently(
                    model_name="event",
                    index=models.Index(
                        fields=["recipient_id"], name="recipient_id_idx"
                    ),
                ),
            ],
        ),
    ]
