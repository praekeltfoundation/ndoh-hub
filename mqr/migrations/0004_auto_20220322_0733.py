# Generated by Django 2.2.24 on 2022-03-22 07:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mqr", "0003_auto_20220322_0539"),
    ]

    operations = [
        migrations.RenameField(
            model_name="baselinesurveyresult",
            old_name="danger_sign",
            new_name="danger_sign2",
        ),
        migrations.AddField(
            model_name="baselinesurveyresult",
            name="danger_sign1",
            field=models.CharField(
                choices=[
                    ("weight_gain", "Weight gain of 4-5 kilograms"),
                    ("vaginal_bleeding", "Vaginal bleeding"),
                    ("nose_bleeds", "Nose bleeds"),
                    ("skip", "Skip"),
                ],
                default=None,
                max_length=20,
                null=True,
            ),
        ),
    ]
