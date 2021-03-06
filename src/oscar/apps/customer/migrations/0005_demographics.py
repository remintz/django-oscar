# Generated by Django 2.1.4 on 2018-12-13 17:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('customer', '0004_email_save'),
    ]

    operations = [
        migrations.CreateModel(
            name='Demographics',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('birthDate', models.DateField(blank=True)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], max_length=1)),
                ('school_level', models.CharField(choices=[('P', 'Primary'), ('S', 'Secondary'), ('U', 'B.Sc.'), ('G', 'M.Sc.')], max_length=1)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Demographics',
                'verbose_name_plural': 'Demographics',
                'abstract': False,
            },
        ),
    ]
