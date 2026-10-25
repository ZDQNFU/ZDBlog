import re
from uuid import uuid4

from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_vary_headers
from django.utils.crypto import salted_hmac
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from tools.pagination import StandardPagination
from user.permissions import IsSuperAdmin
from .models import Moment, MomentLike
from .serializers import MomentSerializer, MomentAdminSerializer

COOKIE_NAME = 'zdblog_moment_visitor'
COOKIE_SALT = 'moment.visitor'
COOKIE_AGE = 365 * 24 * 60 * 60


class MomentPagination(StandardPagination):
    page_size = 10
    max_page_size = 50


class VisitorMixin:
    """点赞身份绑定签名 Cookie；点赞表只保存标识摘要，不依赖登录。"""

    def get_visitor_key(self):
        if not hasattr(self, '_visitor_id'):
            visitor_id = self.request.get_signed_cookie(
                COOKIE_NAME, default=None, salt=COOKIE_SALT, max_age=COOKIE_AGE,
            )
            self._new_visitor = not (isinstance(visitor_id, str) and re.fullmatch(r'[0-9a-f]{32}', visitor_id))
            self._visitor_id = uuid4().hex if self._new_visitor else visitor_id
        return salted_hmac('moment.like', self._visitor_id, algorithm='sha256').hexdigest()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(self, '_new_visitor', False):
            response.set_signed_cookie(COOKIE_NAME, self._visitor_id, salt=COOKIE_SALT,
                                       max_age=COOKIE_AGE, httponly=True,
                                       secure=request.is_secure(), samesite='Lax')
        response['Cache-Control'] = 'private, no-store'
        patch_vary_headers(response, ['Cookie'])
        return response


class MomentListView(VisitorMixin, generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = MomentSerializer
    pagination_class = MomentPagination
    filter_backends = []

    def get_queryset(self):
        visitor_key = self.get_visitor_key()
        return Moment.objects.filter(is_published=True).select_related('author').annotate(
            like_count=Count('likes'),
            viewer_has_liked=Exists(MomentLike.objects.filter(moment_id=OuterRef('pk'), visitor_key=visitor_key)),
        ).order_by('-created_at', '-id')


class MomentLikeThrottle(AnonRateThrottle):
    scope = 'moment_like'
    rate = '30/min'


class MomentLikeView(VisitorMixin, APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [MomentLikeThrottle]

    def _set_like(self, pk, liked):
        visitor_key = self.get_visitor_key()
        with transaction.atomic():
            moment = get_object_or_404(Moment.objects.select_for_update(), pk=pk, is_published=True)
            if liked:
                MomentLike.objects.get_or_create(moment=moment, visitor_key=visitor_key)
            else:
                MomentLike.objects.filter(moment=moment, visitor_key=visitor_key).delete()
            return Response({'liked': liked, 'like_count': moment.likes.count()})

    def post(self, request, pk):
        return self._set_like(pk, True)

    def delete(self, request, pk):
        return self._set_like(pk, False)


class MomentAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = MomentAdminSerializer
    pagination_class = MomentPagination
    search_fields = ['content', 'author__username']

    def get_queryset(self):
        queryset = Moment.objects.select_related('author').annotate(like_count=Count('likes'))
        published = self.request.query_params.get('is_published')
        if published in ('true', 'false'):
            queryset = queryset.filter(is_published=published == 'true')
        return queryset.order_by('-created_at', '-id')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MomentAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = MomentAdminSerializer
    queryset = Moment.objects.select_related('author').annotate(like_count=Count('likes'))
