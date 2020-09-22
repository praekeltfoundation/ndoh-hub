# Generated by Django 2.2.13 on 2020-09-21 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("registrations", "0021_add_jembi_submission")]

    operations = [
        migrations.CreateModel(
            name="WhatsAppContactV2",
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
                (
                    "msisdn",
                    models.CharField(
                        help_text="The MSISDN of the contact", max_length=100
                    ),
                ),
                (
                    "whatsapp_id",
                    models.CharField(
                        blank=True,
                        help_text="The WhatsApp ID of the contact",
                        max_length=100,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "WhatsApp Contact",
                "permissions": (
                    ("can_prune_whatsappcontact", "Can prune WhatsApp contact"),
                ),
            },
        ),
        migrations.AddIndex(
            model_name="whatsappcontactv2",
            index=models.Index(fields=["msisdn"], name="registratio_msisdn_6a68d1_idx"),
        ),
    ]