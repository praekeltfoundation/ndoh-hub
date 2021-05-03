# Generated by Django 2.2.20 on 2021-05-03 01:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RedirectUrls',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('urls', models.CharField(blank=True, max_length=255, null=True)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='RedirectUrlsEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('urls', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='ada.RedirectUrls')),
            ],
        ),
    ]
