# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2018-02-12 07:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("changes", "0006_auto_20170718_1414")]

    operations = [
        migrations.AlterField(
            model_name="change",
            name="action",
            field=models.CharField(
                choices=[
                    ("baby_switch", "Change from pregnancy to baby messaging"),
                    ("pmtct_loss_switch", "Change to loss messaging via pmtct app"),
                    ("pmtct_loss_optout", "Optout due to loss via pmtct app"),
                    ("pmtct_nonloss_optout", "Optout not due to loss via pmtct app"),
                    ("nurse_update_detail", "Update nurseconnect detail"),
                    ("nurse_change_msisdn", "Change nurseconnect msisdn"),
                    ("nurse_optout", "Optout from nurseconnect"),
                    (
                        "momconnect_loss_switch",
                        "Change to loss messaging via momconnect app",
                    ),
                    ("momconnect_loss_optout", "Optout due to loss via momconnect app"),
                    (
                        "momconnect_nonloss_optout",
                        "Optout not due to loss via momconnect app",
                    ),
                    (
                        "momconnect_change_language",
                        "Change the language of the messages via momconnect app",
                    ),
                    (
                        "momconnect_change_msisdn",
                        "Change the MSISDN to send messages to via momconnect app",
                    ),
                    (
                        "momconnect_change_identification",
                        "Change the identification type and number via momconnect app",
                    ),
                    (
                        "admin_change_subscription",
                        "Change the message set and/or language of the specified subscription from admin",
                    ),
                    (
                        "switch_channel",
                        "Switch which channel (eg. SMS, WhatsApp) to receive messages on",
                    ),
                ],
                max_length=255,
            ),
        )
    ]
