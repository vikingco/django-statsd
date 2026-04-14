import time

from django_statsd.clients import statsd

_task_start_times = {}


def on_before_task_publish(sender=None, **kwds):
    """
    Handle Celery ``before_task_publish`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.before_task_publish'.format(sender.replace('.', '_')))


def on_after_task_publish(sender=None, **kwds):
    """
    Handle Celery ``after_task_publish`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.after_task_publish'.format(sender.replace('.', '_')))


def on_task_prerun(sender=None, task_id=None, **kwds):
    """
    Handle Celery ``task_prerun``signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.start'.format(sender.name.replace('.', '_')))

    # Keep track of start times. (For logging the duration in the postrun.)
    _task_start_times[task_id] = time.time()


def on_task_postrun(sender=None, task_id=None, **kwds):
    """
    Handle Celery ``task_postrun`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.done'.format(sender.name.replace('.', '_')))

    # Log duration.
    start_time = _task_start_times.pop(task_id, False)
    if start_time:
        ms = int((time.time() - start_time) * 1000)
        statsd.timing('celery.{}.runtime'.format(sender.name.replace('.', '_')), ms)


def on_task_success(sender=None, **kwds):
    """
    Handle Celery ``task_success`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.success'.format(sender.name.replace('.', '_')))


def on_task_failure(sender=None, task_id=None, task=None, **kwds):
    """
    Handle Celery ``task_failure`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.failure'.format(sender.name.replace('.', '_')))


def on_task_retry(sender=None, **kwds):
    """
    Handle Celery ``task_retry`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.retry'.format(sender.name.replace('.', '_')))


def on_task_revoked(sender=None, **kwds):
    """
    Handle Celery ``task_revoked`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.revoked'.format(sender.name.replace('.', '_')))


def on_task_unknown(sender=None, name=None, **kwds):
    """
    Handle Celery ``task_unknown`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.{}.unknown'.format(name.replace('.', '_')))


def on_task_rejected(sender=None, **kwds):
    """
    Handle Celery ``task_rejected`` signals.
    """
    # Increase statsd counter.
    statsd.incr('celery.rejected')


def register_celery_events():
    try:
        from celery import signals
    except ImportError:  # pragma: no cover
        raise ImportError(
            'Cannot import celery.signals. This dependency is required when STATSD_CELERY_SIGNALS is True.'
        )
    else:
        signals.before_task_publish.connect(on_before_task_publish)
        signals.after_task_publish.connect(on_after_task_publish)
        signals.task_prerun.connect(on_task_prerun)
        signals.task_postrun.connect(on_task_postrun)
        signals.task_success.connect(on_task_success)
        signals.task_failure.connect(on_task_failure)
        signals.task_retry.connect(on_task_retry)
        signals.task_revoked.connect(on_task_revoked)
        signals.task_unknown.connect(on_task_unknown)
        signals.task_rejected.connect(on_task_rejected)
