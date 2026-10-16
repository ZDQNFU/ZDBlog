import json
import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from tools.generate_nums import generate_uuid7
from user.permissions import IsSuperAdmin
from .models import ChatConversation, ChatMessage, ChatPersona
from .serializers import (ConversationSerializer, MessageSerializer,
                          PersonaSerializer, PublicPersonaSerializer)

logger = logging.getLogger(__name__)
LEASE_TIME = timedelta(minutes=15)


def is_busy(conversation):
    return bool(conversation.generation_id and conversation.generation_started_at
                and conversation.generation_started_at > timezone.now() - LEASE_TIME)


class ConversationInput(serializers.Serializer):
    persona_id = serializers.PrimaryKeyRelatedField(queryset=ChatPersona.objects.filter(is_active=True))
    title = serializers.CharField(max_length=100, required=False, default='新聊天')


class StreamInput(serializers.Serializer):
    conversation_id = serializers.CharField(max_length=32)
    message = serializers.CharField(max_length=10000)


class ChatAdminPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PersonaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PublicPersonaSerializer
    queryset = ChatPersona.objects.filter(is_active=True)
    pagination_class = None


class PersonaManageListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = PersonaSerializer
    pagination_class = ChatAdminPagination

    def get_queryset(self):
        search = self.request.query_params.get('search', '').strip()
        return ChatPersona.objects.filter(Q(name__icontains=search) | Q(description__icontains=search))


class PersonaManageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = PersonaSerializer
    queryset = ChatPersona.objects.all()


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = ChatConversation.objects.filter(user=request.user)
        return Response({'conversations': ConversationSerializer(conversations, many=True).data})

    def post(self, request):
        data = ConversationInput(data=request.data)
        data.is_valid(raise_exception=True)
        persona = data.validated_data['persona_id']
        conversation = ChatConversation.objects.create(
            user=request.user, persona=persona, title=data.validated_data['title'],
            persona_name=persona.name, system_prompt=persona.system_prompt, greeting=persona.greeting,
            persona_tools=persona.tools,
        )
        return Response(ConversationSerializer(conversation).data, status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_object_or_404(ChatConversation, pk=pk, user=request.user)
        return Response({'conversation': ConversationSerializer(conversation).data,
                         'messages': MessageSerializer(conversation.messages.order_by('created_at', 'id'), many=True).data})

    def patch(self, request, pk):
        conversation = get_object_or_404(ChatConversation, pk=pk, user=request.user)
        data = ConversationSerializer(conversation, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        data.save()
        return Response(data.data)

    @transaction.atomic
    def delete(self, request, pk):
        conversation = get_object_or_404(ChatConversation.objects.select_for_update(), pk=pk, user=request.user)
        if is_busy(conversation):
            return Response({'detail': '此聊天正在回复，请稍后删除'}, status=409)
        conversation.delete()
        return Response(status=204)


class ChatStreamView(APIView):
    # Retains the existing staff/superuser chat access policy.
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        data = StreamInput(data=request.data)
        data.is_valid(raise_exception=True)
        message = data.validated_data['message']
        generation_id = generate_uuid7()
        with transaction.atomic():
            conversation = get_object_or_404(
                ChatConversation.objects.select_for_update(),
                pk=data.validated_data['conversation_id'], user=request.user,
            )
            if is_busy(conversation):
                return Response({'detail': '此聊天正在回复，请稍后再发送'}, status=409)
            if conversation.generation_id:
                conversation.agent_messages = []
            # Invalidate old state after a failed/disconnected previous turn.
            conversation.generation_id = generation_id
            conversation.generation_started_at = timezone.now()
            if conversation.title == '新聊天':
                conversation.title = message[:40]
            conversation.save(update_fields=['generation_id', 'generation_started_at', 'title', 'agent_messages', 'updated_at'])
            previous_messages = list(conversation.messages.order_by('created_at', 'id').values('role', 'content'))
            ChatMessage.objects.create(user=request.user, conversation=conversation, role='user',
                                       content=message, token_count=len(message.encode('utf-8')))

        def event_stream():
            full_response = []
            final_state = []
            completed = False
            try:
                from .agent import build_agent
                from .utils import stream_chat_with_agent
                from langchain_core.messages import AIMessage, HumanMessage, messages_from_dict, messages_to_dict
                history = messages_from_dict(conversation.agent_messages) if conversation.agent_messages else [
                    HumanMessage(content=m['content']) if m['role'] == 'user' else AIMessage(content=m['content'])
                    for m in previous_messages
                ]
                graph = build_agent(conversation.system_prompt, tool_names=conversation.persona_tools)
                def remember_state(state):
                    final_state[:] = [state]
                for token in stream_chat_with_agent(graph, message, str(conversation.pk), history=history,
                                                     on_state=remember_state):
                    full_response.append(token)
                    yield f'data: {json.dumps({"token": token}, ensure_ascii=False)}\n\n'
                completed = True
            except Exception:
                logger.exception('Chat generation failed for conversation %s', conversation.pk)
                yield f'data: {json.dumps({"error": "回复失败，请稍后重试"}, ensure_ascii=False)}\n\n'
            finally:
                # A lease token prevents a late worker overwriting a newer turn.
                with transaction.atomic():
                    current = ChatConversation.objects.select_for_update().filter(
                        pk=conversation.pk, generation_id=generation_id,
                    ).first()
                    if current:
                        content = ''.join(full_response).rstrip()
                        if content:
                            ChatMessage.objects.create(user=request.user, conversation=current, role='ai',
                                                       content=content, token_count=len(content.encode('utf-8')))
                        current.agent_messages = messages_to_dict(final_state[-1]) if completed and final_state else []
                        current.generation_id = ''
                        current.generation_started_at = None
                        current.save(update_fields=['agent_messages', 'generation_id', 'generation_started_at', 'updated_at'])
            if completed:
                yield f'data: {json.dumps({"done": True})}\n\n'

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Never silently combine different conversations into model context.
        conversation = get_object_or_404(ChatConversation, pk=request.query_params.get('conversation_id'), user=request.user)
        return Response({'messages': MessageSerializer(conversation.messages.all(), many=True).data})


class ChatUserListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            return Response({'detail': '分页参数必须是整数'}, status=400)
        users = User.objects.filter(chat_messages__isnull=False,
                                    username__icontains=request.query_params.get('search', '').strip()).annotate(
            message_count=Count('chat_messages'), last_active=Max('chat_messages__created_at'),
        ).order_by('-last_active', 'id')
        count = users.count()
        results = list(users.values('id', 'username', 'message_count', 'last_active')[(page - 1) * page_size:page * page_size])
        return Response({'results': results, 'count': count})


class ChatUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        conversations = list(ChatConversation.objects.filter(user=user))
        conversation_id = request.query_params.get('conversation_id')
        if conversation_id:
            conversation = get_object_or_404(ChatConversation, pk=conversation_id, user=user)
        else:
            conversation = conversations[0] if conversations else None
        messages = ChatMessage.objects.none()
        if conversation:
            messages = ChatMessage.objects.filter(user=user, conversation=conversation).order_by('created_at', 'id')
        paging_requested = 'page' in request.query_params or 'page_size' in request.query_params
        message_count = messages.count() if paging_requested else None
        page = 1
        page_size = 20
        if paging_requested:
            try:
                page = int(request.query_params.get('page', 1))
                page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
                if page < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return Response({'detail': '分页参数必须是正整数'}, status=400)
            pages = max(1, (message_count + page_size - 1) // page_size)
            page = min(page, pages)
            messages = messages[(page - 1) * page_size:page * page_size]
        response = {'user': {'id': user.id, 'username': user.username},
                    'conversations': ConversationSerializer(conversations, many=True).data,
                    'selected_conversation_id': conversation.pk if conversation else '',
                    'messages': MessageSerializer(messages, many=True).data}
        if paging_requested:
            response.update(count=message_count, page=page, page_size=page_size,
                            num_pages=max(1, (message_count + page_size - 1) // page_size))
        return Response(response)


class ChatClearView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @transaction.atomic
    def post(self, request, user_id):
        get_object_or_404(User, pk=user_id)
        conversations = list(ChatConversation.objects.select_for_update().filter(user_id=user_id))
        if any(is_busy(c) for c in conversations):
            return Response({'detail': '该用户有正在回复的聊天，请稍后清理'}, status=409)
        deleted, _ = ChatMessage.objects.filter(user_id=user_id).delete()
        ChatConversation.objects.filter(user_id=user_id).update(agent_messages=[], generation_id='', generation_started_at=None)
        return Response({'detail': f'已清空 {deleted} 条记录'})


class ChatTrimView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @transaction.atomic
    def post(self, request, user_id):
        get_object_or_404(User, pk=user_id)
        try:
            days = int(request.data.get('days', 30))
            if days < 1 or days > 36500:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'detail': '天数必须是 1 到 36500 的整数'}, status=400)
        conversations = list(ChatConversation.objects.select_for_update().filter(user_id=user_id))
        if any(is_busy(c) for c in conversations):
            return Response({'detail': '该用户有正在回复的聊天，请稍后清理'}, status=409)
        deleted, _ = ChatMessage.objects.filter(user_id=user_id, created_at__lt=timezone.now() - timedelta(days=days)).delete()
        ChatConversation.objects.filter(user_id=user_id).update(agent_messages=[], generation_id='', generation_started_at=None)
        return Response({'detail': f'已清理 {deleted} 条记录，保留最近 {days} 天'})
