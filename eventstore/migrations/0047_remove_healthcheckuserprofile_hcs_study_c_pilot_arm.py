# Generated by Django 2.2.24 on 2021-09-30 17:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eventstore', '0046_auto_20210712_1223'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='healthcheckuserprofile',
            name='hcs_study_c_pilot_arm',
        ),
    ]