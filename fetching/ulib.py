#!/usr/bin/env python

from eventlet import channel, timer, api
from eventlet.api import TimeoutError, exc_after
from collections import deque
from Queue import Empty

class _SilentException:
    pass

class FakeTimer:
    def cancel(self):
        pass

class timeout(object):
    def __init__(self, seconds, *throw_args):
        self.seconds = seconds
        if seconds is None:
            return
        if not throw_args:
            self.throw_args = (TimeoutError(), )
        elif throw_args == (None, ):
            self.throw_args = (_SilentException(), )
        else:
            self.throw_args = throw_args

    def __enter__(self):
        if self.seconds is None:
            self.timer = FakeTimer()
        else:
            self.timer = exc_after(self.seconds, *self.throw_args)
        return self.timer

    def __exit__(self, typ, value, tb):
        self.timer.cancel()
        if typ is _SilentException and value in self.throw_args:
            return True


class Queue(object):
    def __init__(self):
        self.contents = deque()
        self.channel = channel.channel()
        self._jobs = 0
    def put(self, item, block=True):
        self.contents.append(item)
        self._jobs += 1
        if block:
            self.pump()
    def put_nowait(self, item):
        return self.put(item, False)
    def put_all(self, iterable, block=True):
        for item in iterable:
            self.put_nowait(item)
        if block:
            self.pump()
    def get(self, block=True):
        if self.contents:
            return self.contents.popleft()
        if not block:
            raise Empty
        return self.channel.receive()
    def get_nowait(self):
        return self.get(False)
    def unget(self, item, block=False):
        self.contents.appendleft(item)
        if block:
            self.pump()
    def pump(self):
        while self.contents and self.channel.balance < 0:
            self.channel.send(self.contents.popleft())
    def remove(self, item):
        return self.contents.remove(item)
    def empty(self):
        return not self.contents
    def task_done(self):
        if self._jobs == 0:
            raise ValueError("Tasks completed exceeds number of tasks")
        self._jobs -= 1
    def join(self):
        while self._jobs > 0:
            api.sleep(0.1)
    def qsize(self):
        return len(self)
    def __len__(self):
        return len(self.contents)
    def __contains__(self, item):
        return item in self.contents

