# Generated by Django 2.1.2 on 2018-10-18 08:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0015_auto_20181015_1002")]

    operations = [
        migrations.AlterField(
            model_name="registration",
            name="registrant_id",
            field=models.CharField(db_index=True, max_length=36, null=True),
        )
    ]
