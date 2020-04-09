# Generated by Django 2.2.8 on 2020-04-07 14:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("eventstore", "0024_auto_20200407_1242")]

    operations = [
        migrations.AddField(
            model_name="covid19triage",
            name="difficulty_breathing",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="covid19triage",
            name="province",
            field=models.CharField(
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
    ]