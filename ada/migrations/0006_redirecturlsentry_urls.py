# Generated by Django 2.2.20 on 2021-05-03 13:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ada', '0005_remove_redirecturlsentry_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='redirecturlsentry',
            name='urls',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ada.RedirectUrl'),
        ),
    ]
