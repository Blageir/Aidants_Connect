# Generated by Django 2.2.4 on 2019-08-27 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("aidants_connect_web", "0002_journal")]

    operations = [
        migrations.RemoveField(model_name="journal", name="demarches"),
        migrations.AddField(
            model_name="journal",
            name="demarche",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
