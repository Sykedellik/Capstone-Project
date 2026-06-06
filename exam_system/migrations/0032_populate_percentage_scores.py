# Data migration to populate percentage_score for existing records

from django.db import migrations


def populate_percentage_scores(apps, schema_editor):
    ExamAttempt = apps.get_model('exam_system', 'ExamAttempt')
    ExamResult = apps.get_model('exam_system', 'ExamResult')
    
    # Update ExamAttempt records
    for attempt in ExamAttempt.objects.filter(status='completed'):
        if attempt.total_questions > 0:
            attempt.percentage_score = round((attempt.score / attempt.total_questions) * 100, 2)
            attempt.save(update_fields=['percentage_score'])
    
    # Update ExamResult records
    for result in ExamResult.objects.all():
        if result.total_questions > 0:
            result.percentage_score = round((result.score / result.total_questions) * 100, 2)
            result.save(update_fields=['percentage_score'])


class Migration(migrations.Migration):

    dependencies = [
        ('exam_system', '0031_rename_total_add_percentage_score'),
    ]

    operations = [
        migrations.RunPython(populate_percentage_scores, migrations.RunPython.noop),
    ]