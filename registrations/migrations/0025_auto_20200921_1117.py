# Generated by Django 2.2.13 on 2020-09-21 11:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0024_delete_whatsappcontact")]

    operations = [
        migrations.RenameModel(
            old_name="WhatsAppContactV2", new_name="WhatsAppContact"
        ),
        migrations.RemoveIndex(
            model_name="whatsappcontact", name="registratio_msisdn_6a68d1_idx"
        ),
        migrations.AddIndex(
            model_name="whatsappcontact",
            index=models.Index(fields=["msisdn"], name="registratio_msisdn_856962_idx"),
        ),
    ]
