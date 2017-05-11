from django.conf.urls import url

from django_statsd.views import record

urlpatterns = [
    url('^record$', record, name='django_statsd.record'),
]
