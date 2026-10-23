from message.models import Message
from tools.content_moderation import moderate_content


def moderate_message(content, *, user):
    return moderate_content(content, model=Message, author=user, author_field='user', label='留言')
