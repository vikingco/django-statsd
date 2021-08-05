from __future__ import absolute_import
from datetime import datetime, timedelta
from importlib import import_module

from django.conf import settings


class StatsdClientProxy:
    """
    A proxy class for the actual StatsdClient. This will instantiate a new client every 2 minutes, so that if the statsd
    host changes IP, we'll do a DNS lookup to discover it instead of sending the UDP packets into the void.
    """
    _client = None

    def __getattribute__(self, name):
        if name == '_client':
            return super().__getattribute__(name)

        refresh_cutoff = datetime.now() - timedelta(seconds=getattr(settings, 'STATSD_REFRESH_SECONDS', 120))
        if self._client is None or not hasattr(self._client, 'created_at') or self._client.created_at < refresh_cutoff:
            client = getattr(settings, 'STATSD_CLIENT', 'statsd.client')
            host = getattr(settings, 'STATSD_HOST', 'localhost')
            port = getattr(settings, 'STATSD_PORT', 8125)
            prefix = getattr(settings, 'STATSD_PREFIX', None)
            self._client = import_module(client).StatsClient(host=host, port=port, prefix=prefix)
            self._client.created_at = datetime.now()

        return self._client.__getattribute__(name)


statsd = StatsdClientProxy()
