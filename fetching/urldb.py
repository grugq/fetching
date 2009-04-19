#!/usr/bin/env python

import ulib
import xmlrpclib

class URLDB(object):
    def __init__(self):
        self.queue = ulib.Queue()

    def refresh(self):
        pass

    def get(self):
        if len(self.queue) == 0:
            self.refresh()
        return self.queue.get()

    def put(self, val, blocking=True):
        return self.queue.put(val, blocking)

    def put_all(self, iterable):
        self.queue.put_all(iterable)

    def failure(self, url):
        self.put(url)

    def done(self, url):
        pass

    def join(self):
        self.queue.join()
    def task_done(self):
        self.queue.task_done()

class FileURLDB(URLDB):
    def __init__(self, fname, max_errors=2):
        super(FileURLDB, self).__init__()
        self.fname = fname
        self.fp = open(fname)
        self.max_errors = max_errors
        self.faillog = open(fname + ".fail", 'a')
        self.failures = {}

    def refresh(self):
        for i,l in zip(xrange(1000), self.fp):
            self.put(l.strip())

    def failure(self, url):
        error = self.failures.get(url, 0)

        if error > self.max_errors:
            self.faillog.write("%s\n" % url)
            self.faillog.flush()
            del self.failures[url]
        else:
            self.failures[url] = error + 1
            self.put(url)

class RemoteURLDB(URLDB):
    def __init__(self, remote):
        super(FileURLDB, self).__init__()
        self._proxy = xmlrpclib.ServerProxy(remote)

    def refresh(self):
        for l in self._proxy.get(100):
            self.put(l.strip())

    def failure(self, url):
        self._proxy.failure(url)


def opendb(uri, *args, **kwargs):
    if uri.startswith("file://"):
        return FileURLDB(uri[7:], *args, **kwargs)
    elif uri.startswith("http://") or uri.startswith("https://"):
        return RemoteURLDB(uri, *args, **kwargs)
    raise RuntimeError("Unknown uri scheme: %s" % uri)
