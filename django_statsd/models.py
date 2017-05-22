from __future__ import absolute_import
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django_statsd.clients import statsd

from .celery_hooks import register_celery_events


if getattr(settings, 'STATSD_CELERY_SIGNALS', False):  # pragma: no cover
    register_celery_events()


def model_save(sender, **kwargs):
    """
    Handle ``save`` events of all Django models.
    """
    instance = kwargs.get('instance')

    # Increase statsd counter.
    statsd.incr('models.%s.%s.%s' % (
        instance._meta.app_label,
        instance._meta.object_name,
        'create' if kwargs.get('created', False) else 'update',
    ))


def model_delete(sender, **kwargs):
    """
    Handle ``delete`` events of all Django models.
    """
    instance = kwargs.get('instance')

    # Increase statsd counter.
    statsd.incr('models.%s.%s.delete' % (
        instance._meta.app_label,
        instance._meta.object_name,
    ))


if getattr(settings, 'STATSD_MODEL_SIGNALS', False):  # pragma: no cover
    post_save.connect(model_save)
    post_delete.connect(model_delete)


def logged_in(sender, request, user, **kwargs):
    statsd.incr('auth.login.success')
    statsd.incr('auth.backends.%s' % user.backend.replace('.', '_'))


def logged_out(sender, request, user, **kwargs):
    statsd.incr('auth.logout.success')


def login_failed(sender, credentials, **kwargs):
    statsd.incr('auth.login.failed')


if getattr(settings, 'STATSD_AUTH_SIGNALS', False):  # pragma: no cover
    user_logged_in.connect(logged_in)
    user_logged_out.connect(logged_out)
    user_login_failed.connect(login_failed)
