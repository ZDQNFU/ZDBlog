from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from .views import VisitorGeoView


@override_settings(CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
}})
class VisitorGeoTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def response_for(self, rows, view=None):
        with patch('tracking_api.views.Visitor.objects.filter') as visitor_filter:
            queryset = visitor_filter.return_value.values.return_value.annotate.return_value.order_by.return_value
            queryset.iterator.return_value = iter(rows)
            return (view or VisitorGeoView()).get(None)

    def test_reserved_test_ips_do_not_consume_public_ip_limit(self):
        rows = [{'ip_address': f'198.18.0.{index}'} for index in range(1, 251)]
        rows.extend([{'ip_address': '113.118.113.77'}, {'ip_address': '8.8.8.8'}])
        view = VisitorGeoView()
        view.MAX_PUBLIC_IPS = 1
        # Query the real bundled XDB; no HTTP call is permitted.
        with patch('requests.sessions.Session.request', side_effect=AssertionError('Unexpected HTTP request')):
            response = self.response_for(rows, view)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['points'][0]['ip'], '113.118.113.77')
        self.assertEqual(response.data['points'][0]['region'], '广东省')
        self.assertEqual(response.data['summary']['benchmark_ips'], 250)
        self.assertEqual(response.data['summary']['public_ips'], 2)
        self.assertTrue(response.data['summary']['limited'])
        self.assertEqual(response.data['cached_count'], 0)
        cached = self.response_for(rows, view)
        self.assertEqual(cached.data['cached_count'], 1)

    def test_non_public_visits_explain_empty_result_without_cache_or_lookup(self):
        rows = [{'ip_address': ip} for ip in ['198.18.1.1', '127.0.0.1', '::1', 'invalid']]
        with patch('tracking_api.views.cache.get_many') as get_many, patch.object(VisitorGeoView, '_fetch_ip_geo') as lookup:
            response = self.response_for(rows)
        get_many.assert_not_called()
        lookup.assert_not_called()
        self.assertEqual(response.data['empty_reason'], 'no_public_ips')
        self.assertEqual(response.data['summary']['total_ips'], 4)
        self.assertEqual(response.data['summary']['benchmark_ips'], 1)
        self.assertEqual(response.data['summary']['invalid_ips'], 1)

    def test_missing_local_dependency_is_error_instead_of_empty_success(self):
        with patch.object(VisitorGeoView, '_fetch_ip_geo', side_effect=ImportError('missing ip2region')):
            with self.assertLogs('tracking_api.views', level='ERROR'):
                response = self.response_for([{'ip_address': '113.118.113.77'}])
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('points', response.data)

    def test_ipv6_uses_bundled_offline_database(self):
        result = VisitorGeoView()._fetch_ip_geo('240e:3b7:3272:d8d0:db09:c067:8d59:539e')
        self.assertEqual(result['region'], '广东省')
        self.assertIsInstance(result['lat'], float)
        self.assertIsInstance(result['lon'], float)
