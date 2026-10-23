"""Conservative local rules: block clear abuse, queue suspicious content for review."""
import re
import unicodedata
from datetime import timedelta

from django.utils import timezone

from article.models import Comment, CommentModerationKeyword
from article.services.comment_text import content_fingerprint, normalize


LINK_PATTERN = re.compile(r'(?:https?://|www\.)[^\s<>]+', re.IGNORECASE)


def moderate_comment(content, *, author):
    text = normalize(content)
    matching = Comment.objects.filter(content_fingerprint=content_fingerprint(content))
    last_manual_decision = matching.filter(
        reviewed_at__isnull=False, status__in=[Comment.STATUS_APPROVED, Comment.STATUS_REJECTED],
    ).order_by('-reviewed_at', '-pk').values_list('status', flat=True).first()
    if last_manual_decision != Comment.STATUS_APPROVED and matching.filter(
        status=Comment.STATUS_REJECTED,
    ).exists():
        return Comment.STATUS_REJECTED, '自动拦截：与已拒绝的评论内容相同'

    spam_text = ''.join(c for c in unicodedata.normalize('NFKC', content).casefold()
                        if not c.isspace() and unicodedata.category(c) != 'Cf')
    keywords = list(CommentModerationKeyword.objects.filter(enabled=True).values(
        'word', 'normalized_word', 'action',
    ))
    for action, result in ((CommentModerationKeyword.ACTION_REJECT, Comment.STATUS_REJECTED),
                           (CommentModerationKeyword.ACTION_REVIEW, Comment.STATUS_PENDING)):
        for keyword in keywords:
            if keyword['action'] == action and keyword['normalized_word'] in text:
                label = '拦截' if result == Comment.STATUS_REJECTED else '待审'
                return result, f'命中{label}关键词：{keyword["word"]}'
    if len(LINK_PATTERN.findall(unicodedata.normalize('NFKC', content))) >= 3:
        return Comment.STATUS_PENDING, '评论包含多个外部链接，等待人工复核'
    if re.search(r'(.)\1{11,}', spam_text):
        return Comment.STATUS_PENDING, '疑似重复字符刷屏，等待人工复核'

    recent = Comment.objects.filter(
        author=author, created_at__gte=timezone.now() - timedelta(minutes=5),
    ).order_by('-created_at').values_list('content', flat=True)[:30]
    if any((normalize(previous) == text if text else previous.strip() == content.strip())
           for previous in recent):
        return Comment.STATUS_PENDING, '短时间重复提交相同评论，等待人工复核'
    return Comment.STATUS_APPROVED, '自动审核通过'
