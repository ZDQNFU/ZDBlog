"""Public comment trees and their denormalized article counters."""
from collections import defaultdict

from article.models import Comment


def visible_comment_ids(article_id):
    children = defaultdict(list)
    for comment_id, parent_id in Comment.objects.filter(
        article_id=article_id, status=Comment.STATUS_APPROVED,
    ).values_list('id', 'parent_id'):
        children[parent_id].append(comment_id)

    visible = set()
    stack = list(children[None])
    while stack:
        comment_id = stack.pop()
        if comment_id not in visible:
            visible.add(comment_id)
            stack.extend(children[comment_id])
    return visible


def public_comment_tree(article_id):
    children = defaultdict(list)
    comments = list(Comment.objects.filter(
        article_id=article_id, status=Comment.STATUS_APPROVED,
    ).select_related('author').order_by('created_at', 'id'))
    for comment in comments:
        children[comment.parent_id].append(comment)
    for comment in comments:
        comment.prefetched_replies = children[comment.id]
    # An approved reply remains hidden while any ancestor is not approved.
    return children[None]
