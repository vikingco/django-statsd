from __future__ import absolute_import
from importlib import import_module
from django.conf import settings


def get_client():
    client = getattr(settings, 'STATSD_CLIENT', 'statsd.client')
    host = getattr(settings, 'STATSD_HOST', 'localhost')
    port = getattr(settings, 'STATSD_PORT', 8125)
    prefix = getattr(settings, 'STATSD_PREFIX', None)
    return import_module(client).StatsClient(host=host, port=port, prefix=prefix)


statsd = get_client()
