# Generated by Django 4.2.13 on 2024-07-16 09:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("eventstore", "0066_whatsapptemplatesendstatus_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="whatsapptemplatesendstatus",
            old_name="registration_completed_at",
            new_name="action_completed_at",
        ),
        migrations.AlterField(
            model_name="whatsapptemplatesendstatus",
            name="status",
            field=models.CharField(
                choices=[
                    ("wired", "Message wired"),
                    ("event_received", "Event received"),
                    ("action_completed", "Action completed"),
                ],
                default="wired",
                max_length=30,
            ),
        ),
    ]
