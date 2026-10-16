"""Legacy /auth/chat routes share the current implementation and permissions."""
from chat_robot.views import (
    ChatStreamView, ChatHistoryView, ChatUserListView,
    ChatUserDetailView, ChatClearView, ChatTrimView,
)
