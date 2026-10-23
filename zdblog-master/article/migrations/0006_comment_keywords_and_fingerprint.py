import hashlib
import json
import unicodedata

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


INITIAL_REJECT_WORDS = {
    '辱骂或人身攻击': [
        '傻逼', '傻屄', '傻b', '煞笔', '傻叉', '操你妈', '草你妈', '艹你妈',
        '去你妈的', '你妈死了', 'nmsl', 'fuck you', 'motherfucker',
    ],
    '暴力威胁': ['弄死你', '杀了你全家', '杀光你们', '人肉你全家'],
    '色情、赌博或诈骗招揽': [
        '成人视频', '裸聊加', '约炮加', '澳门赌场', '真人博彩',
        '代开假发票', '代办假证', '刷单返佣', '稳赚不赔带单',
    ],
}
INITIAL_REVIEW_WORDS = ['加微信', '加vx', '加qq', '进群领取', '扫码领取', '推广合作', '代刷', '博彩', '裸聊']


def normalize(word):
    return ''.join(c for c in unicodedata.normalize('NFKC', word).casefold() if c.isalnum())


def migrate_words_and_fingerprints(apps, schema_editor):
    alias = schema_editor.connection.alias
    Keyword = apps.get_model('article', 'CommentModerationKeyword')
    Comment = apps.get_model('article', 'Comment')
    Config = apps.get_model('system_config', 'SystemConfig')
    for description, words in INITIAL_REJECT_WORDS.items():
        for word in words:
            Keyword.objects.using(alias).create(word=word, normalized_word=normalize(word),
                                                action='reject', description=description, source='builtin')
    for word in INITIAL_REVIEW_WORDS:
        Keyword.objects.using(alias).create(word=word, normalized_word=normalize(word),
                                            action='review', description='疑似推广或敏感内容', source='builtin')

    for config in Config.objects.using(alias).filter(key__in=['COMMENT_BLOCK_WORDS', 'COMMENT_REVIEW_WORDS']):
        try:
            words = json.loads(config.value)
            if config.is_encrypted or not isinstance(words, list) or len(words) > 1000 or any(
                not isinstance(word, str) or len(word) > 100 or not normalize(word) for word in words
            ):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise ValueError(f'{config.key} 词库格式异常，请先修正为未加密的 JSON 字符串数组再迁移') from exc
        action = 'reject' if config.key == 'COMMENT_BLOCK_WORDS' else 'review'
        for word in words:
            keyword, created = Keyword.objects.using(alias).get_or_create(
                normalized_word=normalize(word),
                defaults={'word': word.strip(), 'action': action, 'source': 'custom',
                          'description': '从旧系统配置迁入'},
            )
            # Preserve the old rule priority when the same term occurs in both lists.
            if not created and action == 'reject' and keyword.action != 'reject':
                Keyword.objects.using(alias).filter(pk=keyword.pk).update(action='reject')
        Config.objects.using(alias).filter(pk=config.pk).update(
            description='已迁移至评论管理 → 审核关键词；此配置仅保留历史值，不再读取',
        )

    for comment in Comment.objects.using(alias).only('pk', 'content').iterator():
        normalized = unicodedata.normalize('NFKC', comment.content).casefold()
        canonical = ''.join(
            c for c in normalized
            if not c.isspace() and unicodedata.category(c) not in ('Cf', 'Cc')
            and not unicodedata.category(c).startswith('P')
        )
        fingerprint = hashlib.sha256((canonical or normalized.strip()).encode('utf-8')).hexdigest()
        Comment.objects.using(alias).filter(pk=comment.pk).update(content_fingerprint=fingerprint)


class Migration(migrations.Migration):
    dependencies = [
        ('article', '0005_comment_moderation'),
        ('system_config', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='comment', name='content_fingerprint',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=64, verbose_name='内容指纹'),
        ),
        migrations.CreateModel(
            name='CommentModerationKeyword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=100, verbose_name='关键词')),
                ('normalized_word', models.CharField(editable=False, max_length=200, unique=True, verbose_name='匹配词')),
                ('action', models.CharField(choices=[('reject', '直接拒绝'), ('review', '进入待审')], default='reject', max_length=10, verbose_name='处理方式')),
                ('enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='分类或备注')),
                ('source', models.CharField(choices=[('builtin', '内置'), ('custom', '自定义')], default='custom', max_length=10, verbose_name='来源')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_comment_keywords', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_comment_keywords', to=settings.AUTH_USER_MODEL, verbose_name='修改人')),
            ],
            options={'db_table': 'article_comment_keyword', 'verbose_name': '评论审核关键词',
                     'verbose_name_plural': '评论审核关键词', 'ordering': ['-created_at', '-pk']},
        ),
        migrations.RunPython(migrate_words_and_fingerprints, migrations.RunPython.noop),
    ]
