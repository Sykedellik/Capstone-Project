from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exam_system', '0019_remove_profile_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='questions',
            field=models.ManyToManyField(blank=True, related_name='exams', to='exam_system.Question'),
        ),
    ]
