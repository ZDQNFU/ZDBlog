import json
import os
import sqlite3
from datetime import datetime, timedelta

import msgpack
from django.contrib.auth.models import User
from django.db.models import Count, Max, Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage
from user.permissions import IsSuperAdmin


def _estimate_tokens(text):
    """Rough token estimation: ~1.3 tokens per character for CJK text, ~0.3 for ASCII."""
    return len(text.encode('utf-8'))


# ---------- SQLite checkpoint helpers (keeps LangGraph state in sync with MySQL) ----------

def _get_db_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'data', 'asuka_memory.db')


def _get_conn():
    return sqlite3.connect(_get_db_path())


def _decode_checkpoint(blob):
    return msgpack.unpackb(blob)


def _delete_checkpoints_for_thread(thread_id):
    """Delete all checkpoints and writes for a thread in SQLite."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM writes WHERE thread_id = ?', (thread_id,))
        cursor.execute('DELETE FROM checkpoints WHERE thread_id = ?', (thread_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def _trim_checkpoints_for_thread(thread_id, keep_days):
    """Delete checkpoints older than keep_days for a thread in SQLite."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()

        cursor.execute(
            'SELECT checkpoint_id, checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY rowid ASC',
            (thread_id,)
        )
        rows = cursor.fetchall()

        deleted = 0
        for cp_id, blob in rows:
            cp = _decode_checkpoint(blob)
            ts = cp.get('ts', '')
            if ts and ts < cutoff:
                cursor.execute(
                    'DELETE FROM writes WHERE thread_id = ? AND checkpoint_id = ?',
                    (thread_id, cp_id)
                )
                cursor.execute(
                    'DELETE FROM checkpoints WHERE thread_id = ? AND checkpoint_id = ?',
                    (thread_id, cp_id)
                )
                deleted += 1
        conn.commit()
        return deleted
    finally:
        conn.close()


class ChatStreamView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        message = request.data.get('message', '').strip()
        if not message:
            return Response({'detail': '消息不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        thread_id = str(request.user.id)

        def event_stream():
            ChatMessage.objects.create(
                user=request.user,
                role='user',
                content=message,
                token_count=_estimate_tokens(message),
            )

            from chat_robot.agent import agent
            from chat_robot.utils import stream_chat_with_agent

            full_response = []
            try:
                for token in stream_chat_with_agent(agent, message, thread_id):
                    full_response.append(token)
                    yield f'data: {json.dumps({"token": token})}\n\n'
            except Exception as e:
                yield f'data: {json.dumps({"error": str(e)})}\n\n'
            finally:
                ai_content = ''.join(full_response).rstrip()
                if ai_content.strip():
                    ChatMessage.objects.create(
                        user=request.user,
                        role='ai',
                        content=ai_content,
                        token_count=_estimate_tokens(ai_content),
                    )
            yield f'data: {json.dumps({"done": True})}\n\n'

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class ChatHistoryView(APIView):
    """获取当前用户最近30天的聊天记录"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = timezone.now() - timedelta(days=30)
        messages = ChatMessage.objects.filter(
            user=request.user,
            created_at__gte=since,
        ).order_by('created_at')

        return Response({
            'messages': [
                {'role': m.role, 'content': m.content, 'created_at': m.created_at}
                for m in messages
            ],
        })


# ---------- S-end chat management (superadmin only) ----------

class ChatUserListView(APIView):
    """列出有聊天记录的所有用户"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        qs = ChatMessage.objects.values('user_id').annotate(
            message_count=Count('id'),
            last_active=Max('created_at'),
        )

        users = []
        for row in qs:
            user = User.objects.filter(pk=row['user_id']).first()
            if not user:
                continue
            if search and search.lower() not in user.username.lower():
                continue
            users.append({
                'id': user.id,
                'username': user.username,
                'message_count': row['message_count'],
                'last_active': row['last_active'],
            })

        users.sort(key=lambda u: u['last_active'] or '', reverse=True)

        total = len(users)
        start = (page - 1) * page_size
        paged = users[start:start + page_size]

        return Response({'results': paged, 'count': total})


class ChatUserDetailView(APIView):
    """查看某个用户的全部聊天记录"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        messages = ChatMessage.objects.filter(
            user_id=user_id,
        ).order_by('created_at')

        return Response({
            'user': {'id': user.id, 'username': user.username},
            'messages': [
                {'role': m.role, 'content': m.content, 'created_at': m.created_at}
                for m in messages
            ],
        })


class ChatClearView(APIView):
    """清空某用户的聊天记录（MySQL + SQLite）"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, user_id):
        try:
            User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        deleted, _ = ChatMessage.objects.filter(user_id=user_id).delete()
        _delete_checkpoints_for_thread(str(user_id))
        return Response({'detail': f'已清空 {deleted} 条记录'})


class ChatTrimView(APIView):
    """只保留某用户最近 N 天的聊天记录（MySQL + SQLite）"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, user_id):
        try:
            User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        keep_days = int(request.data.get('days', 30))
        if keep_days < 1:
            return Response({'detail': '天数必须 >= 1'}, status=status.HTTP_400_BAD_REQUEST)

        cutoff = timezone.now() - timedelta(days=keep_days)
        deleted, _ = ChatMessage.objects.filter(
            user_id=user_id,
            created_at__lt=cutoff,
        ).delete()
        _trim_checkpoints_for_thread(str(user_id), keep_days)
        return Response({'detail': f'已清理 {deleted} 条记录，保留最近 {keep_days} 天'})
