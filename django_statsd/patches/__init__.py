from __future__ import absolute_import
from django.conf import settings
from importlib import import_module


def import_patches():
    patches = getattr(settings, 'STATSD_PATCHES', [])
    for patch in patches:
        import_module(patch).patch()


import_patches()
