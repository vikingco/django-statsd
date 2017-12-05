DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}
MIDDLEWARE = []
MIDDLEWARE_CLASSES = []
INSTALLED_APPS = ['django_statsd', ]

ROOT_URLCONF = 'django_statsd.urls'
STATSD_CLIENT = 'django_statsd.clients.null'
STATSD_PREFIX = None
STATSD_PATCHES = []
STATSD_VIEW_TIMER_DETAILS = True
STATSD_CELERY_SIGNALS = True
STATSD_MODEL_SIGNALS = True
STATSD_AUTH_SIGNALS = True

SECRET_KEY = 'secret'
LANGUAGE_CODE = 'en-us'
USE_I18N = False

STATSD_RECORD_KEYS = ['window.performance.navigation.redirectCount',
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
                      'window.performance.timing.unloadEventStart',]
