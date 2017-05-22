DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}
MIDDLEWARE = []

ROOT_URLCONF = 'django_statsd.urls'
STATSD_CLIENT = 'django_statsd.clients.null'
STATSD_PREFIX = None

SECRET_KEY = 'secret'
LANGUAGE_CODE = 'en-us'
USE_I18N = False
