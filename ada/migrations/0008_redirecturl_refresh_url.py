# Generated by Django 2.2.20 on 2021-05-04 04:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ada', '0007_auto_20210504_0408'),
    ]

    operations = [
        migrations.AddField(
            model_name='redirecturl',
            name='refresh_url',
            field=models.CharField(default='http://127.0.0.1:8000', max_length=200),
        ),
    ]
