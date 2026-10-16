"""Resolve an explicit place before requesting Open-Meteo forecasts."""
import math
import re
import requests

GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
PROVINCES = ('内蒙古自治区', '广西壮族自治区', '宁夏回族自治区', '新疆维吾尔自治区',
             '西藏自治区', '香港特别行政区', '澳门特别行政区', '内蒙古',
             '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
             '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
             '广东', '广西', '海南', '四川', '贵州', '云南', '西藏', '陕西', '甘肃',
             '青海', '宁夏', '新疆', '台湾', '香港', '澳门')
MUNICIPALITIES = {'北京', '天津', '上海', '重庆', '香港', '澳门'}
WEATHER_CODES = {
    0: '晴', 1: '大部晴朗', 2: '多云', 3: '阴', 45: '雾', 48: '冻雾',
    51: '小毛毛雨', 53: '中毛毛雨', 55: '强毛毛雨', 56: '轻冻毛毛雨', 57: '强冻毛毛雨',
    61: '小雨', 63: '中雨', 65: '大雨', 66: '轻冻雨', 67: '强冻雨',
    71: '小雪', 73: '中雪', 75: '大雪', 77: '雪粒',
    80: '小阵雨', 81: '中阵雨', 82: '强阵雨', 85: '小阵雪', 86: '强阵雪',
    95: '雷暴', 96: '雷暴伴小冰雹', 99: '雷暴伴大冰雹',
}


class LocationError(ValueError):
    pass


def admin_name(value):
    return re.sub(r'(壮族自治区|回族自治区|维吾尔自治区|自治区|特别行政区|省|市)$', '', value or '')


def city_name(value):
    return re.sub(r'(市|县|区)$', '', value or '')


def get_json(url, params):
    response = requests.get(url, params=params, timeout=(3, 8))
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or data.get('error'):
        raise ValueError('Weather provider returned invalid data')
    return data


def resolve_location(location):
    location = re.sub(r'\s+', ' ', location.strip())
    if not location or len(location) > 120:
        raise LocationError('请提供要查询的城市及省份，例如“安徽宿州”。不能用服务器位置代替你的所在地。')
    chinese = bool(re.search(r'[\u4e00-\u9fff]', location))
    city, province = location, ''
    compact = re.sub(r'\s+', '', location).removeprefix('中国')
    if chinese:
        city = compact
        for prefix in PROVINCES:
            if compact.startswith(prefix):
                province = admin_name(prefix)
                city = compact[len(prefix):].lstrip('省市 ,，')
                if not city and province in MUNICIPALITIES:
                    city = province
                break
        if not city:
            raise LocationError('请进一步提供城市，例如“安徽宿州”，仅有省份无法确定天气查询地点。')
    qualifier = f', {province}' if province else ''
    names = [city + qualifier]
    if chinese and not city.endswith(('市', '县', '区')):
        names.extend([city + '市' + qualifier, city + '县' + qualifier])
    for name in dict.fromkeys(names):
        params = {'name': name, 'count': 20, 'language': 'zh', 'format': 'json'}
        if chinese:
            params['countryCode'] = 'CN'
        places = get_json(GEOCODING_URL, params).get('results', [])
        places = [p for p in places if (not province or admin_name(p.get('admin1')) == province)
                  and (not chinese or city_name(p.get('name')) == city_name(city))]
        if not places:
            continue
        # Prefer cities to incidental villages with the same name; do not guess between cities.
        tiers = {'PPLC': 0, 'PPLA': 1, 'PPLA2': 2, 'PPLA3': 3, 'PPLA4': 4}
        best = min(tiers.get(p.get('feature_code'), 5) for p in places)
        places = [p for p in places if tiers.get(p.get('feature_code'), 5) == best]
        unique = {(p['latitude'], p['longitude']): p for p in places}
        if len(unique) != 1:
            labels = [' '.join(filter(None, [p.get('country'), p.get('admin1'), p.get('name')]))
                      for p in list(unique.values())[:5]]
            raise LocationError('找到多个同名地点：' + '；'.join(labels) + '。请补充省份或国家后再查询。')
        place = next(iter(unique.values()))
        lat, lon = float(place['latitude']), float(place['longitude'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Invalid coordinates')
        return place
    raise LocationError(f'未能定位“{location}”，请提供省份和城市的完整名称，例如“安徽省宿州市”。未查询其他城市的天气。')


def number(value, unit):
    if value is None:
        return '暂无数据'
    value = float(value)
    if not math.isfinite(value):
        return '暂无数据'
    return f'{value:g}{unit}'


def description(code):
    return WEATHER_CODES.get(code, '天气状况暂无数据')


def weather_for_location(location, days=3):
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 7:
        return '预报天数应为 1～7 天；默认返回今天起 3 天的天气。'
    try:
        place = resolve_location(location)
        data = get_json(FORECAST_URL, {
            'latitude': place['latitude'], 'longitude': place['longitude'],
            'current': 'temperature_2m,apparent_temperature,weather_code,wind_speed_10m',
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
            'timezone': 'auto', 'forecast_days': days,
        })
        label = ' '.join(dict.fromkeys(filter(None, [place.get('country'), place.get('admin1'), place['name']])))
        lines = [f'查询地点：{label}（纬度 {place["latitude"]}，经度 {place["longitude"]}）',
                 f'当地时区：{data["timezone"]}；数据来源：Open-Meteo，当前天气为模型估计，后续为预报。']
        current = data.get('current') or {}
        if current.get('time'):
            lines.append(f'当前（{current["time"]}）：{description(current.get("weather_code"))}，'
                         f'气温 {number(current.get("temperature_2m"), "°C")}，'
                         f'体感 {number(current.get("apparent_temperature"), "°C")}，'
                         f'风速 {number(current.get("wind_speed_10m"), "km/h")}。')
        daily = data['daily']
        dates = daily['time']
        if not dates:
            raise ValueError('Missing daily weather')
        for i, date in enumerate(dates[:days]):
            lines.append(f'{date}：{description(daily["weather_code"][i])}，'
                         f'最低 {number(daily["temperature_2m_min"][i], "°C")}，'
                         f'最高 {number(daily["temperature_2m_max"][i], "°C")}，'
                         f'最大降水概率 {number(daily["precipitation_probability_max"][i], "%")}。')
        return '\n'.join(lines)
    except LocationError as exc:
        return str(exc)
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return f'“{location}”的天气服务暂时不可用，请稍后重试。未返回其他城市的天气，请勿编造温度或降水数据。'
