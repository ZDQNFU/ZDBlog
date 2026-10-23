"""Comment adapter for the shared content moderation rules."""
from article.models import Comment
from tools.content_moderation import moderate_content


def moderate_comment(content, *, author):
    return moderate_content(content, model=Comment, author=author, author_field='author', label='评论')
