from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from system_config.models import SystemConfig

# 只有列在这里的键允许匿名读取。新增键必须显式加入白名单，
# 避免把 GITHUB_TOKEN 之类的敏感配置通过公开接口泄漏出去。
PUBLIC_CONFIG_KEYS = ('ICP_BEIAN', 'GONGAN_BEIAN')


class PublicSystemConfigView(APIView):
    """页脚等公开位置使用的只读配置；未配置的键返回空字符串。"""

    permission_classes = [AllowAny]
    # 不解析 Authorization，避免浏览器里残留的过期 token 让匿名访客收到 401。
    authentication_classes = []

    def get(self, request):
        values = dict(
            SystemConfig.objects.filter(
                key__in=PUBLIC_CONFIG_KEYS, is_encrypted=False
            ).values_list('key', 'value')
        )
        return Response({key: values.get(key, '') for key in PUBLIC_CONFIG_KEYS})
