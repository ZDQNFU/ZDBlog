import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from django.db.models import Max
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tracking.models import Visitor, Pageview
from django.core.cache import cache
from concurrent.futures import as_completed


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

    # 每次请求最多查询未缓存IP的数量，防止触发 ip-api.com 免费版频率限制（45次/分钟）
    MAX_UNCACHED_PER_REQUEST = 30

    def get(self, request):
        """
        获取所有访问者的IP地理信息
        优化点：
        1. 使用 GROUP BY + MAX(start_time) 替代 DISTINCT，按最近访问时间排序
        2. 使用线程池并发查询第三方API
        3. 使用Redis缓存减少重复查询
        4. 过滤内网IP
        5. 限制每次请求未缓存IP查询数量，避免超时和频率限制
        """
        # 1. 查询最近活跃的不同IP（按最近访问时间排序，限制200个）
        ip_rows = (
            Visitor.objects
            .values('ip_address')
            .annotate(last_visit=Max('start_time'))
            .order_by('-last_visit')
        )[:200]
        ip_list = [row['ip_address'] for row in ip_rows]

        # 2. 过滤内网IP和无效IP
        valid_ips = []
        for ip in ip_list:
            if not ip:
                continue
            # 过滤内网IP
            if ip.startswith(('127.', '192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.')):
                continue
            if ip.startswith('172.2') and int(ip.split('.')[1]) in range(16, 32):
                continue
            valid_ips.append(ip)

        # 3. 先查缓存，分离已缓存和未缓存的IP
        geo_data = []
        uncached_ips = []

        for ip in valid_ips:
            cache_key = f'ip_geo_v2_{ip}'
            cached = cache.get(cache_key)

            if cached is not None and cached.get('lat') is not None:
                # 缓存命中，直接使用
                geo_data.append(cached)
            else:
                # 需要查询
                uncached_ips.append(ip)

        # 4. 限制每次请求查询未缓存IP的数量
        remaining_uncached = 0
        if uncached_ips:
            if len(uncached_ips) > self.MAX_UNCACHED_PER_REQUEST:
                remaining_uncached = len(uncached_ips) - self.MAX_UNCACHED_PER_REQUEST
                uncached_ips = uncached_ips[:self.MAX_UNCACHED_PER_REQUEST]

            logger.info(
                f'Fetching geo data for {len(uncached_ips)} uncached IPs'
                + (f' ({remaining_uncached} remaining for next request)' if remaining_uncached else '')
            )

            with ThreadPoolExecutor(max_workers=min(10, len(uncached_ips))) as executor:
                # 提交所有查询任务
                future_to_ip = {
                    executor.submit(self._fetch_ip_geo, ip): ip
                    for ip in uncached_ips
                }

                # 收集结果
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        result = future.result(timeout=5)
                        if result and result.get('lat') is not None:
                            geo_data.append(result)
                        else:
                            logger.debug(f'No geo data for IP: {ip}')
                    except Exception as e:
                        logger.warning(f'Failed to fetch geo for IP {ip}: {e}')

        # 5. 返回结果
        return Response({
            'points': geo_data,
            'total': len(geo_data),
            'cached_count': len(geo_data) - min(len(uncached_ips), self.MAX_UNCACHED_PER_REQUEST),
            'uncached_count': min(len(uncached_ips), self.MAX_UNCACHED_PER_REQUEST) if uncached_ips else 0,
            'remaining_uncached': remaining_uncached,
        })

    def _fetch_ip_geo(self, ip):
        """
        获取单个IP的地理位置信息
        使用 ip-api.com 免费API
        """
        cache_key = f'ip_geo_v2_{ip}'

        # 双重检查缓存（防止并发时重复查询）
        cached = cache.get(cache_key)
        if cached is not None and cached.get('lat') is not None:
            return cached

        try:
            # 调用第三方API
            resp = requests.get(
                f'http://ip-api.com/json/{ip}',
                params={'lang': 'zh-CN'},
                timeout=3,  # 降低超时时间到3秒
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get('status') == 'success':
                # 成功获取数据
                entry = {
                    'ip': ip,
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                    'city': data.get('city', ''),
                    'country': data.get('country', ''),
                    'region': data.get('regionName', ''),
                    'isp': data.get('isp', ''),
                }
                # 缓存24小时
                cache.set(cache_key, entry, 86400)
                return entry
            else:
                # API返回失败（如私有IP、保留IP等）
                logger.debug(f'IP-API returned failure for {ip}: {data.get("message", "Unknown error")}')
                # 失败时缓存空值1小时，避免频繁重试
                cache.set(cache_key, {}, 3600)
                return {}

        except requests.Timeout:
            logger.warning(f'Timeout fetching geo data for IP: {ip}')
            # 超时时缓存5分钟
            cache.set(cache_key, {}, 300)
            return {}

        except requests.RequestException as e:
            logger.warning(f'Request error fetching geo data for IP {ip}: {e}')
            # 网络错误时缓存5分钟
            cache.set(cache_key, {}, 300)
            return {}

        except Exception as e:
            logger.error(f'Unexpected error fetching geo data for IP {ip}: {e}')
            # 未知错误时缓存10分钟
            cache.set(cache_key, {}, 600)
            return {}

# class VisitorGeoView(APIView):
#     """返回访问者IP地理分布数据（用于地图展示）"""
#     permission_classes = [IsAuthenticated, IsSuperAdmin]
#
#     def get(self, request):
#         from django.core.cache import cache
#
#         visitors = Visitor.objects.values('ip_address').distinct()
#         geo_data = []
#
#         for v in visitors:
#             ip = v['ip_address']
#             if not ip or ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.'):
#                 continue
#
#             cache_key = f'ip_geo_v2_{ip}'
#             cached = cache.get(cache_key)
#             if cached is not None:
#                 if cached.get('lat'):
#                     geo_data.append(cached)
#                 continue
#
#             try:
#                 resp = requests.get(
#                     f'http://ip-api.com/json/{ip}',
#                     params={'lang': 'zh-CN'},
#                     timeout=5,
#                 )
#                 data = resp.json()
#                 if data.get('status') == 'success':
#                     entry = {
#                         'ip': ip,
#                         'lat': data.get('lat'),
#                         'lon': data.get('lon'),
#                         'city': data.get('city', ''),
#                         'country': data.get('country', ''),
#                     }
#                     cache.set(cache_key, entry, 86400)
#                     geo_data.append(entry)
#                 else:
#                     cache.set(cache_key, {}, 3600)
#             except Exception as e:
#                 logger.warning(f'Geo lookup failed for IP {ip}: {e}')
#                 cache.set(cache_key, {}, 600)
#
#         return Response({'points': geo_data})
