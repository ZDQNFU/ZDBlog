import logging
import ipaddress
import json
import threading
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tracking.models import Visitor, Pageview
from django.core.cache import cache


from user.permissions import IsSuperAdmin
from .serializers import VisitorSerializer, PageviewSerializer

logger = logging.getLogger(__name__)


class VisitorListView(generics.ListAPIView):
    """访问日志列表（支持 ?search=IP/用户名 搜索）"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = VisitorSerializer

    def get_queryset(self):
        qs = Visitor.objects.prefetch_related('pageviews').all()
        search = self.request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(ip_address__icontains=search) |
                Q(user__username__icontains=search)
            )
        return qs


class VisitorDetailView(generics.RetrieveDestroyAPIView):
    """访问日志详情 / 删除"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = VisitorSerializer
    lookup_field = 'session_key'

    def get_queryset(self):
        return Visitor.objects.prefetch_related('pageviews').all()


class VisitorDeleteView(APIView):
    """批量删除访问日志"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        keys = request.data.get('session_keys', [])
        if not keys:
            return Response({'detail': '请提供要删除的 session_key 列表'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = Visitor.objects.filter(session_key__in=keys).delete()
        return Response({'detail': f'已删除 {deleted} 条记录'})


class VisitorGeoView(APIView):
    """返回访问者IP地理分布数据（用于地图展示）"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    MAX_PUBLIC_IPS = 200

    def get(self, request):
        """
        通过项目内的 ip2region xdb 离线库查询最近30天访客地域，不访问第三方服务。
        """
        # 公网地址过滤必须在展示数量限制之前，避免保留地址测试数据占满名额。
        ip_rows = (
            Visitor.objects
            .filter(start_time__gte=timezone.now() - timedelta(days=30))
            .values('ip_address')
            .annotate(last_visit=Max('start_time'))
            .order_by('-last_visit', 'ip_address')
        )

        # 2. 过滤内网、保留地址和无效 IP（同时支持 IPv4/IPv6）
        valid_ips = []
        summary = {
            'total_ips': 0, 'public_ips': 0, 'excluded_ips': 0,
            'benchmark_ips': 0, 'invalid_ips': 0,
        }
        benchmark_network = ipaddress.ip_network('198.18.0.0/15')
        for row in ip_rows.iterator(chunk_size=1000):
            ip = row['ip_address']
            summary['total_ips'] += 1
            try:
                address = ipaddress.ip_address(ip)
                if not address.is_global:
                    summary['excluded_ips'] += 1
                    if address.version == 4 and address in benchmark_network:
                        summary['benchmark_ips'] += 1
                    continue
            except (ValueError, TypeError):
                summary['invalid_ips'] += 1
                continue
            summary['public_ips'] += 1
            if len(valid_ips) < self.MAX_PUBLIC_IPS:
                valid_ips.append(ip)

        # 3. 批量读取缓存，再使用本地 xdb 处理未缓存 IP。
        geo_data = []
        uncached_ips = []
        cache_keys = {ip: f'ip_geo_local_v1_{ip}' for ip in valid_ips}
        cached_geo = cache.get_many(cache_keys.values()) if cache_keys else {}
        for ip in valid_ips:
            cached = cached_geo.get(cache_keys[ip])

            if cached is not None:
                # 成功结果和空字典负缓存都算命中，避免失败 IP 每次刷新都重试
                if cached.get('lat') is not None:
                    geo_data.append(cached)
            else:
                # 需要查询
                uncached_ips.append(ip)

        cached_count = len(geo_data)
        new_entries = {}
        try:
            for ip in uncached_ips:
                result = self._fetch_ip_geo(ip)
                new_entries[cache_keys[ip]] = result
                if result.get('lat') is not None and result.get('lon') is not None:
                    geo_data.append(result)
        except Exception:
            logger.exception('Local ip2region database is unavailable')
            return Response(
                {'detail': '本地 IP 地域库加载失败，请检查后端依赖和离线数据库文件。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if new_entries:
            cache.set_many(new_entries, 86400)
        summary['queried_ips'] = len(valid_ips)
        summary['located_ips'] = len(geo_data)
        summary['unmapped_ips'] = len(valid_ips) - len(geo_data)
        summary['limited'] = summary['public_ips'] > len(valid_ips)
        empty_reason = None
        if not geo_data:
            if not summary['total_ips']:
                empty_reason = 'no_visits'
            elif not summary['public_ips']:
                empty_reason = 'no_public_ips'
            else:
                empty_reason = 'no_china_locations'
        return Response({
            'points': geo_data,
            'total': len(geo_data),
            'cached_count': cached_count,
            'pending_count': 0,
            'summary': summary,
            'empty_reason': empty_reason,
        })

    def _fetch_ip_geo(self, ip):
        """从项目内的 ip2region xdb 文件解析 IP，不发起网络请求。"""
        ip_version = ipaddress.ip_address(ip).version
        searcher = _get_ip2region_searcher(ip_version)
        region_text = searcher.search(ip)
        if not region_text:
            return {}

        parts = [part.strip() for part in region_text.split('|')]
        parts.extend([''] * (5 - len(parts)))
        country, province, city, isp, country_code = parts[:5]

        # 当前后台地图是中国地图，国外/无效地域没有可展示坐标。
        if country not in ('中国', 'China'):
            return {}

        province = province if province and province != '0' else city
        coordinates = _province_centers().get(province)
        if not coordinates:
            return {}

        entry = {
            'ip': ip,
            'lon': coordinates[0],
            'lat': coordinates[1],
            'city': city if city and city != '0' else province,
            'country': country,
            'region': province,
            'isp': isp if isp != '0' else '',
            'country_code': country_code,
        }
        return entry


@lru_cache(maxsize=1)
def _province_centers():
    path = Path(__file__).with_name('province_centers.json')
    with path.open(encoding='utf-8') as file:
        return json.load(file)


_ip2region_searchers = {}
_ip2region_buffers = {}
_ip2region_lock = threading.Lock()


def _get_ip2region_searcher(ip_version):
    if ip_version in _ip2region_searchers:
        return _ip2region_searchers[ip_version]

    with _ip2region_lock:
        if ip_version in _ip2region_searchers:
            return _ip2region_searchers[ip_version]

        import ip2region.searcher as xdb
        import ip2region.util as util

        db_path = Path(settings.BASE_DIR).parent / 'models' / 'ip2region' / f'ip2region_v{ip_version}.xdb'
        if not db_path.is_file():
            raise FileNotFoundError(f'未找到离线数据库文件：{db_path}')

        util.verify_from_file(str(db_path))
        buffer = util.load_content_from_file(str(db_path))
        version = util.IPv4 if ip_version == 4 else util.IPv6
        searcher = xdb.new_with_buffer(version, buffer)
        _ip2region_buffers[ip_version] = buffer
        _ip2region_searchers[ip_version] = searcher
        return searcher
