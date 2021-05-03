# Generated by Django 2.2.20 on 2021-05-03 13:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ada', '0003_redirecturl_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='redirecturl',
            name='content',
            field=models.TextField(default='This url has no copy'),
        ),
        migrations.AlterField(
            model_name='redirecturlsentry',
            name='urls',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ada.RedirectUrl'),
        ),
    ]
