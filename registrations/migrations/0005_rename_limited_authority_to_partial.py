# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-12-01 08:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0004_auto_20160722_1019")]

    operations = [
        migrations.AlterField(
            model_name="source",
            name="authority",
            field=models.CharField(
                choices=[
                    (b"patient", b"Patient"),
                    (b"advisor", b"Trusted Advisor"),
                    (b"hw_partial", b"Health Worker Partial"),
                    (b"hw_full", b"Health Worker Full"),
                ],
                max_length=30,
            ),
        )
    ]
