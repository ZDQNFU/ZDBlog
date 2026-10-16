from django.urls import path

from .views import (
    ChatStreamView,
    ChatHistoryView,
    ChatUserListView,
    ChatUserDetailView,
    ChatClearView,
    ChatTrimView,
    PersonaListView, PersonaManageListView, PersonaManageDetailView,
    ConversationListView, ConversationDetailView,
)

urlpatterns = [
    path('personas/', PersonaListView.as_view(), name='chat_personas'),
    path('manage/personas/', PersonaManageListView.as_view(), name='chat_personas_manage'),
    path('manage/personas/<str:pk>/', PersonaManageDetailView.as_view(), name='chat_persona_manage'),
    path('conversations/', ConversationListView.as_view(), name='chat_conversations'),
    path('conversations/<str:pk>/', ConversationDetailView.as_view(), name='chat_conversation'),
    path('stream/', ChatStreamView.as_view(), name='chat_stream'),
    path('history/', ChatHistoryView.as_view(), name='chat_history'),
    path('users/', ChatUserListView.as_view(), name='chat_user_list'),
    path('users/<int:user_id>/', ChatUserDetailView.as_view(), name='chat_user_detail'),
    path('users/<int:user_id>/clear/', ChatClearView.as_view(), name='chat_clear'),
    path('users/<int:user_id>/trim/', ChatTrimView.as_view(), name='chat_trim'),
]
