# Generated by Django 2.2.4 on 2019-10-30 15:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0019_add_whatsapp_postbirth_registration_type")]

    operations = [
        migrations.CreateModel(
            name="ClinicCode",
            fields=[
                ("code", models.CharField(max_length=255)),
                ("value", models.CharField(max_length=255)),
                (
                    "uid",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
            ],
        )
    ]
