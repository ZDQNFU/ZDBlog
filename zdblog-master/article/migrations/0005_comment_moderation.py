from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def refresh_existing_counts(apps, schema_editor):
    Article = apps.get_model('article', 'Article')
    for article in Article.objects.using(schema_editor.connection.alias).annotate(
        total=models.Count('comments'),
    ).iterator():
        Article.objects.using(schema_editor.connection.alias).filter(pk=article.pk).update(
            comment_count=article.total,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('article', '0004_like'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        # Keep existing comments published; only new comments default to pending.
        migrations.AddField(
            model_name='comment', name='status',
            field=models.CharField(
                choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')],
                db_index=True, default='approved', max_length=20, verbose_name='审核状态',
            ), preserve_default=False,
        ),
        migrations.AlterField(
            model_name='comment', name='status',
            field=models.CharField(
                choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')],
                db_index=True, default='pending', max_length=20, verbose_name='审核状态',
            ),
        ),
        migrations.AddField(
            model_name='comment', name='moderation_reason',
            field=models.CharField(blank=True, max_length=255, verbose_name='审核原因'),
        ),
        migrations.AddField(
            model_name='comment', name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='人工审核时间'),
        ),
        migrations.AddField(
            model_name='comment', name='reviewed_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_comments', to=settings.AUTH_USER_MODEL, verbose_name='审核人',
            ),
        ),
        migrations.RunPython(refresh_existing_counts, migrations.RunPython.noop),
    ]
