from django.conf import settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module

_statsd = None


def get(name, default):
    try:
        return getattr(settings, name, default)
    except ImportError:
        return default


def get_client():
    client = get('STATSD_CLIENT', 'statsd.client')
    host = get('STATSD_HOST', 'localhost')
    port = get('STATSD_PORT', 8125)
    prefix = get('STATSD_PREFIX', None)
    return import_module(client).StatsClient(host=host, port=port, prefix=prefix)


if not _statsd:
    _statsd = get_client()

statsd = _statsd
