import subprocess as _subprocess
import time
import types

class Control: pass # as in: yield Control
class Finished: pass
class NULL: pass # distinct value so we can return None

class GeneratorStack(object):
    """
    I maintain a call stack of nested generators.
    """
    def __init__(self, task):
        self.stack = []
        self.task = task
        self.returned = NULL
        self._done = False
        self.input = NULL
        self.waitingForInput = False

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
            if self.waitingForInput:
                if self.input is NULL:
                    pass # do nothing.
                else:
                    next = self.task.send(self.input)
                    self.input = NULL
                    self.waitingForInput = False
            elif self.returned is not NULL:
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
            elif isinstance(next, Input):
                next.send = self._makeInputCallback()
                self.waitingForInput = True
                return next
            else:
                return next

    def _makeInputCallback(self):
        def callback(value):
            self.input = value
        return callback

    def stop(self):
        self._done = True
        
    def isDone(self):
        return self._done
   

class Worker(object):
    """
    I keep multiple generators going simultaneously.
    .assign() generators to me and call .work() or .tick()
    """
    def __init__(self, *tasks):
        self.queue = []  # list of call stacks
        self.values = [] # list of values
        for t in tasks:
            self.assign(t)

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
    I wrap a child process in the operating system.
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
    """
    I wrap return values so that microthreads can behave
    like normal functions (returning one value).
    """
    def __init__(self, value):
        self.value = value

class Value(object):
    """
    I wrap a value so that microthreads can behave
    like normal generators (yielding multiple values).
    """
    def __init__(self, value):
        self.value = value


class Input(object):
    """
    I represent an input prompt.
    """
    def __init__(self, prompt, type=None):
        self.prompt = prompt
        self.type = type

    def send(self, value):
        raise AssertionError("Input.send should have been overridden!")

class Output(object):
    """
    I represent output.
    """
    def __init__(self, value):
        self.value = value
    def __cmp__(self, other):
        return cmp(self.value, other.value)
    def __repr__(self):
        return "Output(%r)" % self.value


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


def wrap(task):
    """
    Runs a task generator to completion.
    Returns the Return() value, if any.
    """
    w = Worker(task)
    w.work()
    if isinstance(w.result, Return):
        return w.result.value

def genwrap(task):
    """
    Runs a task as if it were a normal generator.
    Yields any Value() objects generated by the task.

    calling send() on this object 
    """
    w = Worker(task)
    while True:
        v = w.tick()
        if isinstance(v, Value):
            sent = yield v.value
            if sent is not None:
                task.send(sent)
        elif isinstance(v, Input) or isinstance(v,Output):
            yield v
        elif v is Finished:
            break
    

def flatten(task):
    w = Worker(task)
    while True:
        n = w.tick()
        if n is Finished:
            break
        else:
            yield n

def standalone(genfunc):
    """
    Decorator function. Wraps the
    function with clockwork.genwrap
    """
    def wrapped(*args, **kw):
        return genwrap(genfunc(*args, **kw))
    return wrapped


## module interface ##############################

_mainWorker = Worker()

def spawn(task):
    return _mainWorker.assign(task)


def tick():
    _mainWorker.tick()

