# Generated by Django 2.2.4 on 2019-11-19 09:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0009_auto_20191031_1314")]

    operations = [
        migrations.CreateModel(
            name="ExternalRegistrationID",
            fields=[
                (
                    "id",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                )
            ],
        )
    ]
