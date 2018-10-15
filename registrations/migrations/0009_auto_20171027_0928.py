# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2017-10-27 09:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("registrations", "0008_auto_20170928_1025")]

    operations = [
        migrations.AlterField(
            model_name="registration",
            name="reg_type",
            field=models.CharField(
                choices=[
                    (b"momconnect_prebirth", b"MomConnect pregnancy registration"),
                    (b"momconnect_postbirth", b"MomConnect baby registration"),
                    (
                        b"whatsapp_prebirth",
                        b"WhatsApp MomConnect pregnancy registration",
                    ),
                    (b"nurseconnect", b"Nurseconnect registration"),
                    (b"whatsapp_nurseconnect", b"WhatsApp Nurseconnect registration"),
                    (b"pmtct_prebirth", b"PMTCT pregnancy registration"),
                    (
                        b"whatsapp_pmtct_prebirth",
                        b"WhatsApp PMTCT pregnancy registration",
                    ),
                    (b"pmtct_postbirth", b"PMTCT baby registration"),
                    (b"whatsapp_pmtct_postbirth", b"WhatsApp PMTCT baby registration"),
                    (b"loss_general", b"Loss general registration"),
                ],
                max_length=30,
            ),
        )
    ]
