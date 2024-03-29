# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-08-26 11:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("changes", "0003_auto_20160819_0832")]

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
                ],
                max_length=255,
            ),
        )
    ]
