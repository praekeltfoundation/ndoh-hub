# Generated by Django 2.2.20 on 2021-05-04 11:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ada', '0012_auto_20210504_1037'),
    ]

    operations = [
        migrations.RenameField(
            model_name='redirecturl',
            old_name='urls',
            new_name='url',
        ),
        migrations.RenameField(
            model_name='redirecturlsentry',
            old_name='urls',
            new_name='url',
        ),
    ]
