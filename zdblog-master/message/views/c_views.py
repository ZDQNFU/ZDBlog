from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import Throttled

from message.models import Message, MessageLike
from message.serializers import MessageSerializer, MessageWriteSerializer


class MessageListView(generics.ListAPIView):
    """C端：仅公开审核通过且未隐藏的留言，点赞状态按当前用户计算。"""
    serializer_class = MessageSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Message.objects.filter(is_hidden=0, status=Message.STATUS_APPROVED).select_related('user')
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(viewer_has_liked=Exists(MessageLike.objects.filter(
                message_id=OuterRef('pk'), user=self.request.user,
            )))
        return queryset.order_by('-created_at')


class MessageRateThrottle(UserRateThrottle):
    scope = 'message'
    rate = '5/min'


class MessageCreateView(generics.CreateAPIView):
    """C端：创建留言（登录绑定用户，匿名user为空）"""
    serializer_class = MessageWriteSerializer
    throttle_classes = [MessageRateThrottle]

    def throttled(self, request, wait):
        raise Throttled(wait=wait, detail='留言提交过于频繁，请稍后再试')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class MessageLikeToggleView(APIView):
    """C端：留言点赞/取消点赞（需登录）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            message = Message.objects.get(pk=pk, is_hidden=0, status=Message.STATUS_APPROVED)
        except Message.DoesNotExist:
            return Response({'detail': '留言不存在'}, status=status.HTTP_404_NOT_FOUND)
        try:
            MessageLike.objects.create(message=message, user=request.user)
            message.like_count = message.likes.count()
            message.save(update_fields=['like_count'])
            return Response({'liked': True, 'like_count': message.like_count})
        except IntegrityError:
            return Response({'detail': '已经点过赞了'}, status=status.HTTP_409_CONFLICT)

    def delete(self, request, pk):
        try:
            message = Message.objects.get(pk=pk, is_hidden=0, status=Message.STATUS_APPROVED)
        except Message.DoesNotExist:
            return Response({'detail': '留言不存在'}, status=status.HTTP_404_NOT_FOUND)
        deleted, _ = MessageLike.objects.filter(message=message, user=request.user).delete()
        if deleted:
            message.like_count = message.likes.count()
            message.save(update_fields=['like_count'])
            return Response({'liked': False, 'like_count': message.like_count})
        return Response({'detail': '尚未点赞'}, status=status.HTTP_404_NOT_FOUND)
