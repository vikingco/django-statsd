from __future__ import absolute_import
from django_statsd.clients import statsd
import time

_task_start_times = {}


def on_task_sent(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_sent`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.sent' % task)


def on_task_prerun(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_prerun``signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.start' % task.name)

    # Keep track of start times. (For logging the duration in the postrun.)
    _task_start_times[task_id] = time.time()


def on_task_postrun(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_postrun`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.done' % task.name)

    # Log duration.
    start_time = _task_start_times.pop(task_id, False)
    if start_time:
        ms = int((time.time() - start_time) * 1000)
        statsd.timing('celery.%s.runtime' % task.name, ms)


def on_task_success(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_success`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.success' % task)


def on_task_failure(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_failure`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.failure' % task)


def on_task_retry(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_retry`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.retry' % task)


def on_task_revoked(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_revoked`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.revoked' % task)


def on_task_unknown(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_unknown`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.unknown' % task)


def on_task_rejected(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_rejected`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.%s.rejected' % task)


def register_celery_events():
    try:
        from celery import signals
    except ImportError:
        raise ImportError('Cannot import celery.signals. This dependency is required when STATSD_CELERY_SIGNALS'
                          ' is True.')
    else:
        signals.after_task_publish.connect(on_task_sent)
        signals.task_prerun.connect(on_task_prerun)
        signals.task_postrun.connect(on_task_postrun)
        signals.task_success.connect(on_task_success)
        signals.task_failure.connect(on_task_failure)
        signals.task_retry.connect(on_task_retry)
        signals.task_revoked.connect(on_task_revoked)
        signals.task_unknown.connect(on_task_unknown)
        signals.task_rejected.connect(on_task_rejected)
