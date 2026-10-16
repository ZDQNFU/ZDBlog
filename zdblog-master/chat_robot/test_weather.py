from unittest.mock import patch, Mock
import requests
from django.test import SimpleTestCase
from .weather import resolve_location, weather_for_location, LocationError


def place(name='宿州市', province='安徽', latitude=33.63611, longitude=116.97889):
    return {'name': name, 'admin1': province, 'country': '中国', 'country_code': 'CN',
            'latitude': latitude, 'longitude': longitude, 'feature_code': 'PPLA2'}


def forecast():
    return {'timezone': 'Asia/Shanghai',
            'current': {'time': '2026-10-03T10:00', 'temperature_2m': 20,
                        'apparent_temperature': 19, 'weather_code': 61, 'wind_speed_10m': 8},
            'daily': {'time': ['2026-10-03', '2026-10-04'], 'weather_code': [61, 3],
                      'temperature_2m_max': [25, 24], 'temperature_2m_min': [15, 16],
                      'precipitation_probability_max': [80, None]}}


class WeatherTests(SimpleTestCase):
    @patch('chat_robot.weather.get_json')
    def test_province_city_normalization_and_actual_coordinates(self, get_json):
        get_json.side_effect = [{}, {'results': [place()]}, forecast()]
        output = weather_for_location('安徽省宿州', days=2)
        self.assertEqual(get_json.call_args_list[0].args[1]['name'], '宿州, 安徽')
        self.assertEqual(get_json.call_args_list[1].args[1]['name'], '宿州市, 安徽')
        params = get_json.call_args_list[2].args[1]
        self.assertEqual((params['latitude'], params['longitude']), (33.63611, 116.97889))
        self.assertEqual(params['timezone'], 'auto')
        self.assertNotIn('start_date', params)
        self.assertIn('安徽 宿州市', output)
        self.assertIn('2026-10-04', output)
        self.assertIn('小雨', output)
        self.assertIn('80%', output)
        self.assertIn('暂无数据', output)
        self.assertNotIn('深圳', output)

    @patch('chat_robot.weather.get_json')
    def test_wrong_province_never_produces_weather(self, get_json):
        get_json.return_value = {'results': [place(province='江苏')]}
        output = weather_for_location('安徽宿州')
        self.assertIn('未能定位', output)
        self.assertTrue(all('geocoding-api' in call.args[0] for call in get_json.call_args_list))

    @patch('chat_robot.weather.get_json')
    def test_ambiguous_cities_need_clarification(self, get_json):
        get_json.return_value = {'results': [place(), place(province='江苏', latitude=31.3)]}
        with self.assertRaisesMessage(LocationError, '多个同名地点'):
            resolve_location('Suzhou')
        self.assertEqual(get_json.call_count, 1)

    @patch('chat_robot.weather.get_json')
    def test_city_wins_over_same_named_village(self, get_json):
        city = place(name='北京', province='北京市', latitude=39.9)
        city['feature_code'] = 'PPLC'
        village = {**city, 'feature_code': 'PPL', 'latitude': 30.7}
        get_json.return_value = {'results': [village, city]}
        self.assertEqual(resolve_location('北京')['latitude'], 39.9)

    @patch('chat_robot.weather.get_json')
    def test_missing_place_or_invalid_days_does_not_use_ip(self, get_json):
        self.assertIn('请提供', weather_for_location(''))
        self.assertIn('进一步提供城市', weather_for_location('安徽省'))
        self.assertIn('1～7', weather_for_location('安徽宿州', 8))
        get_json.assert_not_called()

    @patch('chat_robot.weather.get_json', side_effect=requests.Timeout('private-provider-error'))
    def test_timeout_is_safe_and_does_not_expose_exception(self, get_json):
        output = weather_for_location('安徽宿州')
        self.assertIn('暂时不可用', output)
        self.assertNotIn('private-provider-error', output)
        self.assertEqual(get_json.call_count, 1)

    @patch('chat_robot.weather.get_json')
    def test_incomplete_forecast_does_not_fabricate_numbers(self, get_json):
        get_json.side_effect = [{'results': [place()]}, {'timezone': 'Asia/Shanghai', 'daily': {'time': []}}]
        self.assertIn('暂时不可用', weather_for_location('安徽宿州'))

    @patch('chat_robot.weather.requests.get')
    def test_tool_requires_place_and_checks_http_status(self, get):
        from .tools import get_weather
        self.assertIn('location', get_weather.args_schema.model_json_schema()['required'])
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError('503')
        get.return_value = response
        self.assertIn('暂时不可用', get_weather.invoke({'location': '安徽宿州'}))
        response.raise_for_status.assert_called_once()
        self.assertEqual(get.call_args.kwargs['timeout'], (3, 8))

    def test_weather_rule_reaches_existing_conversation_graph(self):
        import runpy
        from .tool_config import WEATHER_RULES
        with patch('chat_robot.utils.get_llm_model', return_value=Mock()):
            factory = runpy.run_module('chat_robot.agent')['build_agent']
        with patch.dict(factory.__globals__, {'create_agent': Mock(return_value='graph')}):
            factory('角色快照', ['get_weather'])
            self.assertEqual(factory.__globals__['create_agent'].call_args.kwargs['system_prompt'],
                             '角色快照' + WEATHER_RULES)
            factory('角色快照', [])
            self.assertEqual(factory.__globals__['create_agent'].call_args.kwargs['system_prompt'], '角色快照')
