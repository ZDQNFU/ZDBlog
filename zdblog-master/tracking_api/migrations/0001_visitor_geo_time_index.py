from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    atomic = False

    dependencies = [
        ('tracking', '0002_auto_20180918_2014'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'tracking_visitor_start_ip_idx '
                'ON tracking_visitor (start_time, ip_address)'
            ),
            reverse_sql=(
                'DROP INDEX CONCURRENTLY IF EXISTS '
                'tracking_visitor_start_ip_idx'
            ),
        ),
    ]
