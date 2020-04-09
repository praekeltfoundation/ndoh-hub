# Generated by Django 2.2.8 on 2020-04-08 09:45

import uuid

from django.db import migrations, models

import registrations.validators


def set_default(apps, schema_editor):
    Covid19Triage = apps.get_model("eventstore", "Covid19Triage")
    Covid19Triage.objects.update(deduplication_id=models.F("id"))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("eventstore", "0025_add_difficulty_breathing")]

    operations = [
        migrations.AddField(
            model_name="covid19triage",
            name="deduplication_id",
            field=models.CharField(default=uuid.uuid4, max_length=255),
        ),
        migrations.RunPython(set_default, noop),
        migrations.AlterField(
            model_name="covid19triage",
            name="deduplication_id",
            field=models.CharField(default=uuid.uuid4, max_length=255, unique=True),
        ),
        migrations.AddField(
            model_name="covid19triage",
            name="gender",
            field=models.CharField(
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
        migrations.AddField(
            model_name="covid19triage",
            name="location",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                validators=[registrations.validators.geographic_coordinate],
            ),
        ),
        migrations.AddField(
            model_name="covid19triage",
            name="muscle_pain",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="covid19triage",
            name="preexisting_condition",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("no", "No"), ("not_sure", "Not sure")],
                default="",
                max_length=9,
            ),
        ),
        migrations.AddField(
            model_name="covid19triage",
            name="smell",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]