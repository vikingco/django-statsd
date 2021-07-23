from __future__ import absolute_import
import logging
import sys

from django.test import override_settings
from logutils import dictconfig
from mock import patch, Mock
from pytest import raises
from six.moves import zip
from testfixtures import log_capture
from time import sleep
from unittest import TestCase

from celery import signals as celery_signals
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.contrib.auth import signals as auth_signals
from django.core.cache import cache as django_cache
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.test import TestCase as DjangoTestCase
from django.test.client import RequestFactory

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from django_statsd import middleware
from django_statsd.clients import StatsdClientProxy
from django_statsd.patches import utils, import_patches
from django_statsd.patches.db import (
    patch as db_patch,
    patched_callproc,
    patched_execute,
    patched_executemany,
)
from django_statsd.patches.cache import (
    patch as cache_patch,
    StatsdTracker,
)
from django_statsd.views import process_key, _process_summaries

cfg = {
    'version': 1,
    'formatters': {},
    'handlers': {
        'test_statsd_handler': {
            'class': 'django_statsd.loggers.errors.StatsdHandler',
        },
    },
    'loggers': {
        'statsd': {
            'handlers': ['test_statsd_handler'],
            'level': 'INFO',
        },
        'test.logging': {
            'handlers': ['test_statsd_handler'],
        },
    },
}


class TestIncr(DjangoTestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_graphite_response(self):
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_response(self.req, self.res)
        assert statsd_mock.incr.called

    def test_graphite_response_authenticated(self):
        self.req.user = Mock()
        if DJANGO_VERSION < (1, 10):
            self.req.user.is_authenticated.return_value = True
        else:
            self.req.user.is_authenticated = True
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.incr.call_count, 2)

    def test_graphite_exception(self):
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_exception(self.req, None)
        assert statsd_mock.incr.called

    def test_graphite_exception_authenticated(self):
        self.req.user = Mock()
        if DJANGO_VERSION < (1, 10):
            self.req.user.is_authenticated.return_value = True
        else:
            self.req.user.is_authenticated = True
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_exception(self.req, None)
        self.assertEqual(statsd_mock.incr.call_count, 2)

    def test_graphite_exception_404(self):
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_exception(self.req, Http404())
        assert not statsd_mock.incr.called

    def test_graphite_exception_404_authenticated(self):
        self.req.user = Mock()
        if DJANGO_VERSION < (1, 10):
            self.req.user.is_authenticated.return_value = True
        else:
            self.req.user.is_authenticated = True
        gmw = middleware.GraphiteMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_exception(self.req, Http404())
        self.assertEqual(statsd_mock.incr.call_count, 0)


class TestTiming(TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_ping_timing(self):
        with patch('django_statsd.management.commands.statsd_ping.statsd') as statsd_mock:
            call_command('statsd_ping', key='test.timing')
        self.assertEqual(statsd_mock.timing.call_count, 1)
        self.assertEqual(statsd_mock.timing.call_args_list[0][0][0], 'test.timing')

    def test_request_timing(self):
        func = lambda x: x  # noqa: E731
        gmw = middleware.GraphiteRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])

    @patch.object(settings, 'STATSD_VIEW_TIMER_DETAILS', False)
    def test_request_timing_without_details(self):
        func = lambda x: x  # noqa: E731
        gmw = middleware.GraphiteRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 1)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__), ]
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])

    def test_request_timing_view_not_a_function(self):
        func = object
        gmw = middleware.GraphiteRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__class__.__module__, func.__class__.__name__),
                 'view.%s.GET' % func.__class__.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])

    def test_request_timing_view_no_timings(self):
        func = object
        gmw = middleware.GraphiteRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
        del self.req._start_time
        gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 0)

    def test_request_timing_exception(self):
        func = lambda x: x  # noqa: E731
        gmw = middleware.GraphiteRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
            gmw.process_exception(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])

    def test_request_timing_tastypie(self):
        func = lambda x: x  # noqa: E731
        gmw = middleware.TastyPieRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), {
                'api_name': 'my_api_name',
                'resource_name': 'my_resource_name'
            })
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 3)
        names = ['view.my_api_name.my_resource_name.GET',
                 'view.my_api_name.GET',
                 'view.GET']
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])

    def test_request_timing_tastypie_fallback(self):
        func = lambda x: x  # noqa: E731
        gmw = middleware.TastyPieRequestTimingMiddleware()
        with patch('django_statsd.middleware.statsd') as statsd_mock:
            gmw.process_view(self.req, func, tuple(), dict())
            gmw.process_response(self.req, self.res)
        self.assertEqual(statsd_mock.timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, statsd_mock.timing.call_args_list):
            self.assertEqual(expected, args[0])


class TestClient(TestCase):

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar')
    def test_toolbar_incr(self):
        statsd = StatsdClientProxy()

        self.assertEqual(statsd.cache, {})
        statsd.incr('testing')
        self.assertEqual(statsd.cache, {'testing|count': [[1, 1]]})

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar')
    def test_toolbar_decr(self):
        statsd = StatsdClientProxy()

        self.assertEqual(statsd.cache, {})
        statsd.decr('testing')
        self.assertEqual(statsd.cache, {'testing|count': [[-1, 1]]})

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar')
    def test_toolbar_timing(self):
        statsd = StatsdClientProxy()

        self.assertEqual(statsd.timings, [])
        statsd.timing('testing', 1)
        self.assertEqual(statsd.timings[0][0], 'testing|timing')
        self.assertEqual(statsd.timings[0][2], 1)

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar')
    def test_toolbar_gauge(self):
        statsd = StatsdClientProxy()

        self.assertEqual(statsd.cache, {})
        statsd.gauge('testing', 1)
        self.assertEqual(statsd.cache, {'testing|gauge': [[1, 1]]})
        statsd.gauge('testing', 1, delta=True)
        self.assertEqual(statsd.cache, {'testing|gauge': [[1, 1], [1, 1]]})

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar')
    def test_toolbar_set(self):
        statsd = StatsdClientProxy()

        self.assertEqual(statsd.cache, {})
        statsd.set('testing', 1)
        self.assertEqual(statsd.cache, {'testing|set': [[1, 1]]})

    @override_settings(STATSD_CLIENT='django_statsd.clients.log')
    @log_capture()
    def test_log_client(self, l):
        statsd = StatsdClientProxy()

        statsd.timing('testing.timing', 1)
        statsd.incr('testing.incr')
        statsd.decr('testing.decr')
        statsd.gauge('testing.gauge', 1)
        l.check(('statsd', 'INFO', 'Timing: testing.timing, 1, 1'),
                ('statsd', 'INFO', 'Increment: testing.incr, 1, 1'),
                ('statsd', 'INFO', 'Decrement: testing.decr, 1, 1'),
                ('statsd', 'INFO', 'Gauge: testing.gauge, 1, 1'))

    @override_settings(STATSD_CLIENT='django_statsd.clients.toolbar', STATSD_REFRESH_SECONDS=2)
    def test_refresh_client(self):
        statsd = StatsdClientProxy()
        statsd.incr('test')
        old_client = statsd._client
        statsd.incr('test')
        self.assertEqual(statsd._client, old_client)
        sleep(1)
        statsd.incr('test')
        self.assertEqual(statsd._client, old_client)
        sleep(1)
        statsd.incr('test')
        self.assertNotEquals(old_client, statsd._client)


class TestSignals(DjangoTestCase):

    def setUp(self):
        class Sender(object):
            def __init__(self):
                self.name = 'testing'

            def __str__(self):
                return self.name

        self.sender = Sender()

    def test_celery_signals(self):
        with patch('django_statsd.celery_hooks.statsd') as statsd_mock:
            celery_signals.before_task_publish.send(sender=self.sender)
            celery_signals.after_task_publish.send(sender=self.sender)
            celery_signals.task_prerun.send(sender=self.sender, task_id='1')
            celery_signals.task_postrun.send(sender=self.sender, task_id='1')
            celery_signals.task_postrun.send(sender=self.sender, task_id='2')
            celery_signals.task_success.send(sender=self.sender)
            celery_signals.task_failure.send(sender=self.sender)
            celery_signals.task_retry.send(sender=self.sender)
            celery_signals.task_revoked.send(sender=self.sender)
            celery_signals.task_unknown.send(sender=self.sender)
            celery_signals.task_rejected.send(sender=self.sender)
        self.assertEqual(statsd_mock.incr.call_count, 8)
        self.assertEqual(statsd_mock.timing.call_count, 1)

    def test_auth_signals(self):
        req = RequestFactory().get('/')
        user = Mock()
        user.backend = 'fake_backend'

        with patch('django_statsd.models.statsd') as statsd_mock:
            auth_signals.user_logged_in.send(self.sender, request=req, user=user)
            auth_signals.user_logged_out.send(self.sender, request=req, user=user)
            auth_signals.user_login_failed.send(self.sender, credentials={})

        self.assertEqual(statsd_mock.incr.call_count, 4)


# This is primarily for Zamboni, which loads in the custom middleware
# classes, one of which, breaks posts to our url. Let's stop that.
@patch.object(settings, 'MIDDLEWARE', [])
@patch.object(settings, 'MIDDLEWARE_CLASSES', [])
class TestRecord(DjangoTestCase):

    urls = 'django_statsd.urls'

    def setUp(self):
        super(TestRecord, self).setUp()
        self.url = reverse('django_statsd_record')
        settings.STATSD_RECORD_GUARD = None
        self.good = {'client': 'boomerang', 'nt_nav_st': 1,
                     'nt_domcomp': 3}
        self.stick = {'client': 'stick',
                      'window.performance.timing.domComplete': 123,
                      'window.performance.timing.domInteractive': 456,
                      'window.performance.timing.domLoading': 789,
                      'window.performance.timing.navigationStart': 0,
                      'window.performance.navigation.redirectCount': 3,
                      'window.performance.navigation.type': 1}

    def test_no_client(self):
        assert self.client.get(self.url).status_code == 400

    def test_no_valid_client(self):
        assert self.client.get(self.url, {'client': 'no'}).status_code == 400

    def test_boomerang_almost(self):
        assert self.client.get(self.url,
                               {'client': 'boomerang'}).status_code == 400

    def test_boomerang_minimum(self):
        content = self.client.get(self.url,
                                  {'client': 'boomerang',
                                   'nt_nav_type': 'undefined',
                                   'nt_nav_st': 1}).content.decode()
        assert(content == 'recorded')

    def test_boomerang_undefined_value(self):
        content = self.client.get(self.url,
                                  {'client': 'boomerang',
                                   'nt_nav_type': 'undefined',
                                   'nt_nav_st': 1}).content.decode()
        assert(content == 'recorded')

    @patch.object(settings, 'STATSD_RECORD_KEYS', ['unknown.key', 'window.performance.timing.navigationStart'])
    def test_boomerang_unknown_key(self):
        content = self.client.get(self.url,
                                  {'client': 'boomerang',
                                   'nt_nav_st': 1}).content.decode()
        assert(content == 'recorded')

    @patch('django_statsd.views.process_key')
    def test_boomerang_something(self, process_key):
        content = self.client.get(self.url, self.good).content.decode()
        assert content == 'recorded'
        assert process_key.called

    def test_boomerang_post(self):
        assert self.client.post(self.url, self.good).status_code == 405

    def test_good_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: None
        assert self.client.get(self.url, self.good).status_code == 200

    def test_good_guard_no_result(self):
        settings.STATSD_RECORD_GUARD = lambda r: False
        assert self.client.get(self.url, self.good).status_code == 200

    def test_bad_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: HttpResponseForbidden()
        assert self.client.get(self.url, self.good).status_code == 403

    def test_bad_guard_not_callable(self):
        settings.STATSD_RECORD_GUARD = [1]
        with raises(ValueError):
            self.client.get(self.url, self.good)

    def test_stick_get(self):
        assert self.client.get(self.url, self.stick).status_code == 405

    @patch('django_statsd.views.process_key')
    def test_stick(self, process_key):
        assert self.client.post(self.url, self.stick).status_code == 200
        assert process_key.called

    def test_stick_start(self):
        data = self.stick.copy()
        del data['window.performance.timing.navigationStart']
        assert self.client.post(self.url, data).status_code == 400

    @patch('django_statsd.views.process_key')
    def test_stick_missing(self, process_key):
        data = self.stick.copy()
        del data['window.performance.timing.domInteractive']
        assert self.client.post(self.url, data).status_code == 200
        assert process_key.called

    def test_stick_garbage(self):
        data = self.stick.copy()
        data['window.performance.timing.domInteractive'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_some_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.redirectCount'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_more_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.type'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400


class TestViewFunctions(DjangoTestCase):

    def test_process_key_timing(self):
        with patch('django_statsd.views.statsd') as statsd_mock:
            process_key(1, 'timing', '1')
            process_key(1, 'timing', '2')
            process_key(2, 'timing', '1')
        values = [0, 1, 0]
        for expected, (args, kwargs) in zip(values, statsd_mock.timing.call_args_list):
            self.assertEqual('timing', args[0])
            self.assertEqual(expected, args[1])

    def test_process_key_navigation_type(self):
        with patch('django_statsd.views.statsd') as statsd_mock:
            process_key(1, 'window.performance.navigation.type', '0')
            process_key(1, 'window.performance.navigation.type', '1')
            process_key(1, 'window.performance.navigation.type', '2')
            process_key(1, 'window.performance.navigation.type', '255')
        names = ['window.performance.navigation.type.navigate',
                 'window.performance.navigation.type.reload',
                 'window.performance.navigation.type.back_forward',
                 'window.performance.navigation.type.reserved', ]
        for expected, (args, kwargs) in zip(names, statsd_mock.incr.call_args_list):
            self.assertEqual(expected, args[0])

    def test_process_key_redirect_count(self):
        with patch('django_statsd.views.statsd') as statsd_mock:
            process_key(1, 'window.performance.navigation.redirectCount', '1')
        self.assertEqual(statsd_mock.incr.call_args_list[0][0][0], 'window.performance.navigation.redirectCount')

    def test_process_key_none(self):
        with patch('django_statsd.views.statsd') as statsd_mock:
            process_key(1, 'random', '1')
        assert not statsd_mock.incr.called
        assert not statsd_mock.timing.called

    def test_process_summaries(self):
        timings = {'window.performance.timing.domComplete': 123,
                   'window.performance.timing.domInteractive': 456,
                   'window.performance.timing.domLoading': 789,
                   'window.performance.timing.navigationStart': 0,
                   'window.performance.timing.responseStart': 5,
                   'window.performance.timing.loadEventEnd': 1000,
                   'window.performance.navigation.redirectCount': 3,
                   'window.performance.navigation.type': 1}
        with patch('django_statsd.views.statsd') as statsd_mock:
            _process_summaries(0, timings)
        assert statsd_mock.timing.called
        self.assertEqual(statsd_mock.timing.call_count, 4)


class TestErrorLog(DjangoTestCase):

    def setUp(self):
        dictconfig.dictConfig(cfg)
        self.log = logging.getLogger('test.logging')

    def division_error(self):
        try:
            1 / 0
        except Exception:
            return sys.exc_info()

    def test_emit(self):
        with patch('django_statsd.loggers.errors.statsd') as statsd_mock:
            self.log.error('blargh!', exc_info=self.division_error())
        assert statsd_mock.incr.call_args[0][0] == 'error.zerodivisionerror'

    def test_not_emit(self):
        with patch('django_statsd.loggers.errors.statsd') as statsd_mock:
            self.log.error('blargh!')
        assert not statsd_mock.incr.called


class TestPatchMethod(DjangoTestCase):

    def setUp(self):
        super(TestPatchMethod, self).setUp()

        class DummyClass(object):

            def sumargs(self, a, b, c=3, d=4):
                return a + b + c + d

            def badfn(self, a, b=2):
                raise ValueError

        self.cls = DummyClass

    def test_late_patching(self):
        """
        Objects created before patching should get patched as well.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return original_fn(self, *args, **kwargs) + 10

        obj = self.cls()
        self.assertEqual(obj.sumargs(1, 2, 3, 4), 10)
        utils.patch_method(self.cls, 'sumargs')(patch_fn)
        self.assertEqual(obj.sumargs(1, 2, 3, 4), 20)

    def test_doesnt_call_original_implicitly(self):
        """
        Original fn must be called explicitly from patched to be
        executed.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return 10

        with self.assertRaises(ValueError):
            obj = self.cls()
            obj.badfn(1, 2)

        utils.patch_method(self.cls, 'badfn')(patch_fn)
        self.assertEqual(obj.badfn(1, 2), 10)

    def test_args_kwargs_are_honored(self):
        """
        Args and kwargs must be honored between calls from the patched to
        the original version.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return original_fn(self, *args, **kwargs)

        utils.patch_method(self.cls, 'sumargs')(patch_fn)
        obj = self.cls()
        self.assertEqual(obj.sumargs(1, 2), 10)
        self.assertEqual(obj.sumargs(1, 1, d=1), 6)
        self.assertEqual(obj.sumargs(1, 1, 1, 1), 4)

    def test_patched_fn_can_receive_arbitrary_arguments(self):
        """
        Args and kwargs can be received arbitrarily with no contraints on
        the patched fn, even if the original_fn had a fixed set of
        allowed args and kwargs.
        """
        def patch_fn(original_fn, self, *args, **kwargs):
            return args, kwargs

        utils.patch_method(self.cls, 'badfn')(patch_fn)
        obj = self.cls()
        self.assertEqual(obj.badfn(1, d=2), ((1,), {'d': 2}))
        self.assertEqual(obj.badfn(1, d=2), ((1,), {'d': 2}))
        self.assertEqual(obj.badfn(1, 2, c=1, d=2), ((1, 2), {'c': 1, 'd': 2}))


class TestApplyPatching(DjangoTestCase):
    @patch.object(settings, 'STATSD_PATCHES', ['django_statsd.patches.db', ])
    def test_patching(self):
        """ Test the patching itself """
        import_patches()


class TestCacheWrappingPatching(DjangoTestCase):
    def test_patching(self):
        """ Test the patching itself """
        cache_patch()

    def test_statsdtracker_basecache(self):
        cache = StatsdTracker(django_cache)
        cache.set('A', 1)
        value = cache.get('A')
        self.assertEqual(value, 1)
        assert cache.default_timeout == 300


class TestCursorWrapperPatching(DjangoTestCase):
    example_queries = {
        'select': 'select * from something;',
        'insert': 'insert (1, 2) into something;',
        'update': 'update something set a=1;',
    }

    def test_patching(self):
        """ Test the patching itself """
        db_patch()

    def test_patched_callproc_calls_timer(self):
        for operation, query in list(self.example_queries.items()):
            with patch('django_statsd.patches.db.statsd') as statsd_mock:
                client = Mock(executable_name='client_executable_name')
                db = Mock(executable_name='name', alias='alias', client=client)
                instance = Mock(db=db)

                patched_callproc(lambda *args, **kwargs: None, instance, query)

                self.assertEqual(statsd_mock.timer.call_count, 1)
                self.assertEqual(statsd_mock.timer.call_args[0][0], 'db.client_executable_name.alias.callproc.%s' % operation)

    def test_patched_execute_calls_timer(self):
        for operation, query in list(self.example_queries.items()):
            with patch('django_statsd.patches.db.statsd') as statsd_mock:
                client = Mock(executable_name='client_executable_name')
                db = Mock(executable_name='name', alias='alias', client=client)
                instance = Mock(db=db)

                patched_execute(lambda *args, **kwargs: None, instance, query)

                self.assertEqual(statsd_mock.timer.call_count, 1)
                self.assertEqual(statsd_mock.timer.call_args[0][0], 'db.client_executable_name.alias.execute.%s' % operation)

    def test_patched_executemany_calls_timer(self):
        for operation, query in list(self.example_queries.items()):
            with patch('django_statsd.patches.db.statsd') as statsd_mock:
                client = Mock(executable_name='client_executable_name')
                db = Mock(executable_name='name', alias='alias', client=client)
                instance = Mock(db=db)

                patched_executemany(lambda *args, **kwargs: None, instance, query)

                self.assertEqual(statsd_mock.timer.call_count, 1)
                self.assertEqual(statsd_mock.timer.call_args[0][0], 'db.client_executable_name.alias.executemany.%s' % operation)
