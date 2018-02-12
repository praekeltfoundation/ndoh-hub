# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2018-02-12 07:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('changes', '0006_auto_20170718_1414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='change',
            name='action',
            field=models.CharField(choices=[(b'baby_switch', b'Change from pregnancy to baby messaging'), (b'pmtct_loss_switch', b'Change to loss messaging via pmtct app'), (b'pmtct_loss_optout', b'Optout due to loss via pmtct app'), (b'pmtct_nonloss_optout', b'Optout not due to loss via pmtct app'), (b'nurse_update_detail', b'Update nurseconnect detail'), (b'nurse_change_msisdn', b'Change nurseconnect msisdn'), (b'nurse_optout', b'Optout from nurseconnect'), (b'momconnect_loss_switch', b'Change to loss messaging via momconnect app'), (b'momconnect_loss_optout', b'Optout due to loss via momconnect app'), (b'momconnect_nonloss_optout', b'Optout not due to loss via momconnect app'), (b'momconnect_change_language', b'Change the language of the messages via momconnect app'), (b'momconnect_change_msisdn', b'Change the MSISDN to send messages to via momconnect app'), (b'momconnect_change_identification', b'Change the identification type and number via momconnect app'), (b'admin_change_subscription', b'Change the message set and/or language of the specified subscription from admin'), (b'switch_channel', b'Switch which channel (eg. SMS, WhatsApp) to receive messages on')], max_length=255),
        ),
    ]
