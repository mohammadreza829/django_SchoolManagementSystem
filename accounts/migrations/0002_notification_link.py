from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="link",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="لینک مقصد"),
        ),
        migrations.AddField(
            model_name="notification",
            name="title",
            field=models.CharField(blank=True, default="", max_length=120, verbose_name="عنوان"),
        ),
    ]
