from rest_framework import generics
from user.permissions import IsSuperAdmin

from system_config.models import SystemConfig
from system_config.serializers import (
    SystemConfigListSerializer,
    SystemConfigDetailSerializer,
    SystemConfigWriteSerializer,
)


class SSystemConfigListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    search_fields = ['key', 'description']
    queryset = SystemConfig.objects.order_by('-updated_at')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SystemConfigListSerializer
        return SystemConfigWriteSerializer


class SSystemConfigRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = SystemConfig.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SystemConfigDetailSerializer
        return SystemConfigWriteSerializer
