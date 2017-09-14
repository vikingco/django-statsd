
def pytest_configure():
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        ROOT_URLCONF='django_statsd.urls',
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'django_statsd',
            'tests',
        ),
        STATSD_CLIENT='django_statsd.clients.null',
        STATSD_PREFIX=None,
        MIDDLEWARE=[],
        STATSD_PATCHES=[],
        STATSD_VIEW_TIMER_DETAILS=True,
        STATSD_CELERY_SIGNALS=True,
        STATSD_MODEL_SIGNALS=True,
        STATSD_AUTH_SIGNALS=True,

        STATSD_RECORD_KEYS=['window.performance.navigation.redirectCount',
                            'window.performance.navigation.type',
                            'window.performance.timing.connectEnd',
                            'window.performance.timing.connectStart',
                            'window.performance.timing.domComplete',
                            'window.performance.timing.domContentLoaded',
                            'window.performance.timing.domInteractive',
                            'window.performance.timing.domLoading',
                            'window.performance.timing.domainLookupEnd',
                            'window.performance.timing.domainLookupStart',
                            'window.performance.timing.fetchStart',
                            'window.performance.timing.loadEventEnd',
                            'window.performance.timing.loadEventStart',
                            'window.performance.timing.navigationStart',
                            'window.performance.timing.redirectEnd',
                            'window.performance.timing.redirectStart',
                            'window.performance.timing.requestStart',
                            'window.performance.timing.responseEnd',
                            'window.performance.timing.responseStart',
                            'window.performance.timing.unloadEventEnd',
                            'window.performance.timing.unloadEventStart', ],
    )

    try:
        import django
        django.setup()
    except AttributeError:
        pass
