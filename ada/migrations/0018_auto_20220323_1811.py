# Generated by Django 2.2.20 on 2022-03-23 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("ada", "0017_auto_20220323_1743")]

    operations = [
        migrations.AlterField(
            model_name="adaassessment",
            name="user_input",
            field=models.TextField(blank=True, null=True),
        )
    ]
