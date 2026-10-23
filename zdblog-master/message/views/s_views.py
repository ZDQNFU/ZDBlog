from rest_framework import generics
from user.permissions import IsSuperAdmin

from message.models import Message
from message.serializers import MessageAdminSerializer


class SMessageListCreateView(generics.ListCreateAPIView):
    """S端：留言列表 & 创建"""
    permission_classes = [IsSuperAdmin]
    search_fields = ['content', 'user__username']
    serializer_class = MessageAdminSerializer

    def get_queryset(self):
        qs = Message.objects.select_related('user', 'reviewed_by').order_by('-created_at')
        review_status = self.request.query_params.get('status')
        if review_status:
            qs = qs.filter(status=review_status)
        after = self.request.query_params.get('created_at_after')
        before = self.request.query_params.get('created_at_before')
        if after:
            qs = qs.filter(created_at__gte=after)
        if before:
            qs = qs.filter(created_at__lte=before)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SMessageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """S端：留言详情 & 更新 & 删除"""
    permission_classes = [IsSuperAdmin]
    lookup_field = 'pk'
    queryset = Message.objects.select_related('user', 'reviewed_by')
    serializer_class = MessageAdminSerializer
