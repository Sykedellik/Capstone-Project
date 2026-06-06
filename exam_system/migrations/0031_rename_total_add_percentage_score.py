# Generated migration to rename total to total_questions and add percentage_score

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exam_system', '0030_change_score_to_integer'),
    ]

    operations = [
        migrations.RenameField(
            model_name='examresult',
            old_name='total',
            new_name='total_questions',
        ),
        migrations.AddField(
            model_name='examresult',
            name='percentage_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='examattempt',
            name='percentage_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='examattempt',
            name='total_questions',
            field=models.IntegerField(default=0),
        ),
    ]