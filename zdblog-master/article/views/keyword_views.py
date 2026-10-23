from rest_framework import generics

from article.models import CommentModerationKeyword
from article.serializers.comment_keyword_serializer import CommentKeywordSerializer
from user.permissions import IsSuperAdmin


class CommentKeywordListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = CommentKeywordSerializer
    search_fields = ['word', 'description']
    queryset = CommentModerationKeyword.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)


class CommentKeywordDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = CommentKeywordSerializer
    queryset = CommentModerationKeyword.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
