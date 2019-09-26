# Generated by Django 2.2.4 on 2019-09-26 12:58

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('eventstore', '0004_create_publicregistration'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrebirthRegistration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('contact_id', models.UUIDField()),
                ('device_contact_id', models.UUIDField()),
                ('id_type', models.CharField(choices=[('sa_id', 'SA ID'), ('passport', 'Passport'), ('dob', 'Date of birth')], max_length=8)),
                ('id_number', models.CharField(blank=True, max_length=13)),
                ('passport_country', models.CharField(blank=True, max_length=2)),
                ('passport_number', models.CharField(blank=True, max_length=255)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('language', models.CharField(max_length=3)),
                ('edd', models.DateField()),
                ('facility_code', models.CharField(max_length=6)),
                ('source', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
