# Generated by Django 2.2.24 on 2022-04-25 09:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mqr", "0008_auto_20220404_0905"),
    ]

    operations = [
        migrations.AlterField(
            model_name="baselinesurveyresult",
            name="marital_status",
            field=models.CharField(
                choices=[
                    ("never_married", "Never married"),
                    ("married", "Married"),
                    ("separated_or_divorced", "Separated or divorced"),
                    ("widowed", "Widowed"),
                    ("partner_or_boyfriend", "Have a partner or boyfriend"),
                    ("skip", "Skip"),
                ],
                default=None,
                max_length=25,
                null=True,
            ),
        ),
    ]
