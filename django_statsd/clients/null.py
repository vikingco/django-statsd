from __future__ import absolute_import
from statsd.client import StatsClient


class StatsClient(StatsClient):
    """A null client that does nothing."""

    def __init__(self, host, port, prefix=None, **kwargs):
        self._prefix = prefix

    def _after(self, data):
        pass
