# Generated by Django 2.2.13 on 2020-09-21 11:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("registrations", "0022_add_whatsapp_contact_v2")]

    operations = [
        migrations.RunSQL(
            """
            INSERT INTO registrations_whatsappcontactv2(msisdn, whatsapp_id, created)
            SELECT msisdn, whatsapp_id, created FROM registrations_whatsappcontact
            """
        )
    ]
