from django.urls import path

from system_config.views.c_views import PublicSystemConfigView
from system_config.views.s_views import (
    SSystemConfigListCreateView,
    SSystemConfigRetrieveUpdateDestroyView,
)

urlpatterns = [
    # ================= C端（公开接口） =================
    # 页脚备案号等公开配置；只返回 PUBLIC_CONFIG_KEYS 白名单内的键
    path('c/public/', PublicSystemConfigView.as_view(), name='c_public_config'),

    # ================= S端（管理接口） =================
    path('s/configs/', SSystemConfigListCreateView.as_view(), name='s_config_list_create'),
    path('s/configs/<int:pk>/', SSystemConfigRetrieveUpdateDestroyView.as_view(), name='s_config_detail'),
]
