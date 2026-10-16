# ip2region offline data

This directory contains the upstream ip2region XDB datasets used for local IP-to-region lookup:

- `ip2region_v4.xdb` — IPv4 data
- `ip2region_v6.xdb` — IPv6 data

The Django backend loads these files into memory on the first regional lookup. Dashboard requests do not call an external IP geolocation service. The upstream XDB result provides country, province/region, city, ISP, and country code; the dashboard places China results at the corresponding province centroid because the data does not include latitude/longitude.

The files were obtained from the [official ip2region repository](https://github.com/lionsoul2014/ip2region). The query client is [`py-ip2region`](https://pypi.org/project/py-ip2region/) (Apache-2.0); the upstream data project is dual-licensed under Apache-2.0 or MIT. The upstream license text is included in `LICENSE.md`. ip2region's bundled IP data is updated irregularly; refresh these files from the official repository when updated regional data is needed.
