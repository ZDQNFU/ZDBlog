import hashlib
import unicodedata

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_fingerprints(apps, schema_editor):
    Message = apps.get_model('message', 'Message')
    messages = Message.objects.using(schema_editor.connection.alias)
    for message in messages.only('pk', 'content').iterator():
        normalized = unicodedata.normalize('NFKC', message.content).casefold()
        canonical = ''.join(
            c for c in normalized
            if not c.isspace() and unicodedata.category(c) not in ('Cf', 'Cc')
            and not unicodedata.category(c).startswith('P')
        )
        fingerprint = hashlib.sha256((canonical or normalized.strip()).encode('utf-8')).hexdigest()
        messages.filter(pk=message.pk).update(content_fingerprint=fingerprint)


class Migration(migrations.Migration):
    dependencies = [
        ('message', '0001_initial'),
        ('article', '0006_comment_keywords_and_fingerprint'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='message', name='content_fingerprint',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=64, verbose_name='内容指纹'),
        ),
        # Keep old visibility and manual hiding unchanged; only new entries default to pending.
        migrations.AddField(
            model_name='message', name='status',
            field=models.CharField(choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')],
                                   db_index=True, default='approved', max_length=20, verbose_name='审核状态'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='message', name='status',
            field=models.CharField(choices=[('pending', '待审核'), ('approved', '已通过'), ('rejected', '已拒绝')],
                                   db_index=True, default='pending', max_length=20, verbose_name='审核状态'),
        ),
        migrations.AddField(
            model_name='message', name='moderation_reason',
            field=models.CharField(blank=True, max_length=255, verbose_name='审核原因'),
        ),
        migrations.AddField(
            model_name='message', name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='人工审核时间'),
        ),
        migrations.AddField(
            model_name='message', name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='reviewed_messages', to=settings.AUTH_USER_MODEL, verbose_name='审核人'),
        ),
        migrations.RunPython(backfill_fingerprints, migrations.RunPython.noop),
    ]
