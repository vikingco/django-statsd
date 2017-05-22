from __future__ import absolute_import
from django_statsd.views import record
from django.conf.urls import url

urlpatterns = [
    url(r'^$', record),
    url(r'^record$', record, name='django_statsd_record'),
]
