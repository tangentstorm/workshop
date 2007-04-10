import subprocess as _subprocess
import time
import types

class Control: pass # as in yield control
class Finished: pass
class NULL: pass # distinct value so we can return None

class GeneratorStack(object):

    def __init__(self, task):
        self.stack = []
        self.task = task
        self.returned = NULL
        self._done = False

    def push(self, task):
        self.stack.append(self.task)
        self.task = task

    def pop(self):
        if self.stack:
            self.task = self.stack.pop()
        else:
            self._done = True

    def tick(self):
        try:
            if self.returned is not NULL:
                next = self.task.send(self.returned)
                self.returned = NULL
            else:
                next = self.task.next()
        except StopIteration:
            self.pop()
            if self._done:
                return Finished
            else:
                return self.tick()
        else:
            if next is Control:
                pass
            elif isinstance(next, types.GeneratorType):
                self.push(next)
                return self.tick()
            elif isinstance(next, Return):
                self.pop()
                if self._done:
                    return next
                else:
                    self.returned = next.value
            else:
                return next

    def stop(self):
        self._done = True
        
    def isDone(self):
        return self._done
   

class Worker(object):

    def __init__(self):
        # queue is a list of call stacks
        self.queue = []
        self.gen = None

    def assign(self, task):
        assert isinstance(task, types.GeneratorType), \
               "assign expects a generator!"
        gs = GeneratorStack(task)
        self.queue.append(gs)
        return gs

    def work(self):
        while self.queue:
            self.doNextTask()

    def tick(self):
        if self.queue:
            return self.doNextTask()

    def doNextTask(self):
        assert self.queue, "nothing in queue"
        task = self.queue.pop(0)
        self.result = task.tick()
        if not task.isDone():
            self.queue.append(task)
        return self.result

class Command(object):
    """
    spawn a child process in the operating system.
    """
    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self):
        proc = _subprocess.Popen(self.cmd,
                                 stderr=_subprocess.PIPE,
                                 stdout=_subprocess.PIPE)
        while proc.poll() is None:
            yield None
        self.stdout = proc.stdout
        self.stderr = proc.stderr      
        

class Return(object):
    def __init__(self, value):
        self.value = value

class Result(object):
    def __init__(self):
        self.value = None

    def __call__(self, value):
        self.value = value

    def __invert__(self):
        return self.value


def sleep(secs):
    """
    waits (at least) secs seconds before resuming.
    """
    last = time.time()
    while True:
        now = time.time()
        if (now - last) <= secs:
            yield None
        else:
            break

def every(secs, func):
    """
    Runs the function func every secs seconds (at most).
    Begins immediately, and runs indefinitely.
    """
    while True:
        yield func()
        yield sleep(secs)


def wrap(gen):
    w = Worker()
    w.assign(gen)
    w.work()
    if isinstance(w.result, Return):
        return w.result.value

def flatten(gen):
    w = Worker()
    w.assign(gen)
    while w.queue:
        n = w.tick()
        if n is Finished:
            break
        else:
            yield n

def encapsulate(genfunc):
    """
    Decorator function. Wraps the
    function with clockwork.flatten.
    """
    def wrapped(*args, **kw):
        return flatten(genfunc(*args, **kw))
    return wrapped


_mainWorker = Worker()

def spawn(gen):
    return _mainWorker.assign(gen)


def tick():
    _mainWorker.tick()

