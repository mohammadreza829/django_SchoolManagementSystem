from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0003_alter_quizattempt_quiz"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="available_from",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="\u062e\u0627\u0644\u06cc \u06cc\u0639\u0646\u06cc \u0645\u062d\u062f\u0648\u062f\u06cc\u062a \u0634\u0631\u0648\u0639 \u0646\u062f\u0627\u0631\u062f",
                verbose_name="\u0641\u0639\u0627\u0644 \u0627\u0632 \u062a\u0627\u0631\u06cc\u062e",
            ),
        ),
        migrations.AddField(
            model_name="quiz",
            name="available_until",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="\u062e\u0627\u0644\u06cc \u06cc\u0639\u0646\u06cc \u0645\u062d\u062f\u0648\u062f\u06cc\u062a \u067e\u0627\u06cc\u0627\u0646 \u0646\u062f\u0627\u0631\u062f",
                verbose_name="\u0641\u0639\u0627\u0644 \u062a\u0627 \u062a\u0627\u0631\u06cc\u062e",
            ),
        ),
    ]
