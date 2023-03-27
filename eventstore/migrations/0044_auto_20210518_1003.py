# Generated by Django 2.2.13 on 2021-05-18 10:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0043_auto_20210511_1316")]

    operations = [
        migrations.AddField(
            model_name="healthcheckuserprofile",
            name="hcs_study_c_pilot_arm",
            field=models.CharField(
                choices=[
                    ("D", "Direct Response"),
                    ("A", "List Randomization List A"),
                    ("B", "List Randomization List B"),
                ],
                default=None,
                max_length=3,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="healthcheckuserprofile",
            name="hcs_study_c_quarantine_arm",
            field=models.CharField(
                choices=[
                    ("C", "Control"),
                    ("T1", "Treatment 1"),
                    ("T2", "Treatment 2"),
                    ("T3", "Treatment 3"),
                ],
                default=None,
                max_length=3,
                null=True,
            ),
        ),
    ]
