# Generated by Django 2.2.24 on 2022-03-23 08:52

import functools

from django.db import migrations, models

import eventstore.validators


class Migration(migrations.Migration):
    dependencies = [
        ("mqr", "0006_auto_20220323_0758"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="baselinesurveyresult",
            name="id",
        ),
        migrations.AlterField(
            model_name="baselinesurveyresult",
            name="msisdn",
            field=models.CharField(
                max_length=255,
                primary_key=True,
                serialize=False,
                validators=[
                    functools.partial(
                        eventstore.validators._phone_number, *(), **{"country": "ZA"}
                    )
                ],
            ),
        ),
    ]
