"""Shared keyword and spam checks for comments and message-board entries."""
import re
import unicodedata
from datetime import timedelta

from django.utils import timezone

from article.models import CommentModerationKeyword
from article.services.comment_text import content_fingerprint, normalize

LINK_PATTERN = re.compile(r'(?:https?://|www\.)[^\s<>]+', re.IGNORECASE)


def moderate_content(content, *, model, author, author_field, label):
    text = normalize(content)
    matching = model.objects.filter(content_fingerprint=content_fingerprint(content))
    last_manual_decision = matching.filter(
        reviewed_at__isnull=False, status__in=[model.STATUS_APPROVED, model.STATUS_REJECTED],
    ).order_by('-reviewed_at', '-pk').values_list('status', flat=True).first()
    if last_manual_decision != model.STATUS_APPROVED and matching.filter(
        status=model.STATUS_REJECTED,
    ).exists():
        return model.STATUS_REJECTED, f'自动拦截：与已拒绝的{label}内容相同'

    keywords = list(CommentModerationKeyword.objects.filter(enabled=True).values(
        'word', 'normalized_word', 'action',
    ))
    for action, result in ((CommentModerationKeyword.ACTION_REJECT, model.STATUS_REJECTED),
                           (CommentModerationKeyword.ACTION_REVIEW, model.STATUS_PENDING)):
        for keyword in keywords:
            if keyword['action'] == action and keyword['normalized_word'] in text:
                action_label = '拦截' if result == model.STATUS_REJECTED else '待审'
                return result, f'命中{action_label}关键词：{keyword["word"]}'

    spam_text = ''.join(c for c in unicodedata.normalize('NFKC', content).casefold()
                        if not c.isspace() and unicodedata.category(c) != 'Cf')
    if len(LINK_PATTERN.findall(unicodedata.normalize('NFKC', content))) >= 3:
        return model.STATUS_PENDING, f'{label}包含多个外部链接，等待人工复核'
    if re.search(r'(.)\1{11,}', spam_text):
        return model.STATUS_PENDING, '疑似重复字符刷屏，等待人工复核'

    # Anonymous visitors are distinct people; do not group them as one author.
    # Their submission frequency is limited by IP at the public write endpoint.
    if author is not None:
        recent = model.objects.filter(**{
            author_field: author, 'created_at__gte': timezone.now() - timedelta(minutes=5),
        }).order_by('-created_at').values_list('content', flat=True)[:30]
        if any((normalize(previous) == text if text else previous.strip() == content.strip())
               for previous in recent):
            return model.STATUS_PENDING, f'短时间重复提交相同{label}，等待人工复核'
    return model.STATUS_APPROVED, '自动审核通过'
