#!/usr/bin/env python
#
#

from __future__ import with_statement

from eventlet import api, coros
import time
import urllib2
import httplib
import mechanize
import logging

from ulib import timeout
import browser

log = logging.getLogger("fetcher")


class Error(Exception):
    def __init__(self, exc=None):
        self.exc = exc
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.exc)

class FetchError(Error): pass
class ProcessError(Error): pass


class ProxiDB(object):
    def __init__(self, fname):
        self.fname = fname
        self.proxies = []
        self.prev_len = 0
    def get(self):
        if len(self.proxies) <= self.prev_len / 3:
            self.proxies.extend(l.strip() for l in open(self.fname))
            self.prev_len = len(self.proxies)
        # XXX might as well explode if we got no proxies here, we can't continue
        return self.proxies.pop(0)
    def put(self, proxy):
        self.proxies.append(proxy)
    def __len__(self):
        return len(self.proxies)

class Fetcher(object):
    '''An object that retrieves and processes a URL
    '''
    def __init__(self, proxidb, urldb, delay=0.0, timeout=600.0):
        self.proxidb = proxidb
        self.urldb = urldb
        self.timeout = timeout
        self.delay = delay
        self.br = browser.IE7()
        self.stopping = False

    def urlopen(self, url, proxy, data=None):
        req = mechanize.Request(url, data)
        req.set_proxy(proxy, 'http')

        with timeout(self.timeout) as timer:
            try:
                return self.br.open(req)
            except (urllib2.URLError, httplib.HTTPException), e:
                raise FetchError(e)
            finally:
                timer.cancel()
                self.br.clear_history()

    def process(self, resp):
        raise NotImplementedError("No process() method is available!")

    def fetch_one(self, url, proxy):
        log.debug("Fetching: %s via: %s", url, proxy)

        try:
            start = time.time()
            rp = self.urlopen(url, proxy=proxy)

            log.info("Fetched [%s] %s in %s", proxy, url, time.time() - start)
        except Exception, e:
            log.debug("Failed fetching '%s', ERROR: %r", url, e)
            raise

        if rp is None:
            log.debug("Failed fetching '%s', ERROR: rp is None", url)
            raise FetchError("Got a None response")

        try:
            log.debug("Processing %s", url)
            self.process(rp)
        except ProcessError, e:
            log.error("Failed processing '%s', ERROR: %r", url, e)
            raise

    def run(self):
        while not self.stopping:
            url = self.urldb.get()
            proxy = self.proxidb.get()

            log.debug("next url: %s, proxy: %s", url, proxy)

            try:
                self.fetch_one(url, proxy)
            except ProcessError, e:
                log.error("Processing error: %r", e)
                self.urldb.failure(url)
            except FetchError, e:
                log.debug("Failure fetching: %r", e)
                self.urldb.put(url)
            except Exception, e:
                log.error("Error: %r", e)
                self.urldb.put(url)
            else:
                self.urldb.done(url)

                # Sleep before returning the proxy to the pool, to reduce chance
                # of reuse
                api.sleep(self.delay)
                self.proxidb.put(proxy)
            finally:
                self.urldb.task_done()

def prop(func):
    return property(doc=func.__doc__, **func())

class FetchPool(object):
    def __init__(self, urldb, proxidb, size=512, *args, **kwargs):
        self.urldb = urldb
        self.proxidb = proxidb
        self.pool = coros.CoroutinePool(min_size=0, max_size=size)
        self.fetchers = [self.create(proxidb, urldb,*args,**kwargs)
                            for i in xrange(size)]

    def create(self, proxidb, urldb, *args, **kwargs):
        return Fetcher(proxidb, urldb, *args, **kwargs)

    def set_processor(self, process):
        for f in self.fetchers:
            f.process = process

    @prop
    def delay():
        def fget(self):
            if self.fetchers:
                return self.fetchers[0].delay
        def fset(self, delay):
            for f in self.fetchers:
                f.delay = delay
        return locals()

    @prop
    def timeout():
        def fget(self):
            if self.fetchers:
                return self.fetchers[0].timeout
        def fset(self, timeout):
            for f in self.fetchers:
                f.timeout = timeout
        return locals()

    def stop(self):
        for f in self.fetchers:
            f.stopping = True

    def run(self, join=False):
        for f in self.fetchers:
            self.pool.execute_async(f.run)
            api.sleep(0)
        if join:
            self.urldb.join()

    def __iter__(self):
        return iter(self.fetchers)
    def __len__(self):
        return len(self.fetchers)
    def __repr__(self):
        return "<%s size=%s delay=%s timeout=%s processor=%s>" % (
            self.__class__.__name__, len(self), self.fetchers[0].delay,
            self.fetchers[0].timeout)
