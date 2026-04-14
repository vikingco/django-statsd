from django.urls import path

from django_statsd.views import record

urlpatterns = [
    path('', record),
    path('record', record, name='django_statsd_record'),
]
