# Generated by Django 2.2.24 on 2022-01-31 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eventstore", "0051_auto_20211213_1038"),
    ]

    operations = [
        migrations.AddField(
            model_name="chwregistration",
            name="age",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="postbirthregistration",
            name="age",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="prebirthregistration",
            name="age",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]