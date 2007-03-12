
# * clockwork: simple asynchronous programming
# **    background
"""

This is basically microthreads:

  - define things to do as generators
  - yield None   to give up control
  - or yield another generator!!

This last one means that your generators
can spawn sub-generators.

@TODO: allow launching threads without waiting

Usage:

w = Worker()
w.assign(yourGenerator)

# and then...

if in_loop:
    w.tick()
else:
    w.work()

You want stuff to happen almost at the same time
but okay to just switch back and forth really fast
if you take too long at one, then the others lock up
so try not to do that!
"""
# **    applications
# ***       use case: vengeance
# ***       use case: kiwi game console
# ***       use case: linkwatcher
# ***       use case: web server
"""
lighttpd uses this approach
"""
# * dependencies
import logging
import sched
import subprocess as _subprocess
import time
import types
import unittest

# * -- implementation --
# * goal: a simple queue of tasks
"""
Our top-level object are called <strong>Workers</strong>. It's
possible to have as many workers hanging around as you like, but you
probably only need one per program.

What a Worker does is very simple. It has a <strong>queue of
work</strong> to do, and it works through the queue as long as there's
work left to do. Here's how it looks:
"""
class WorkerTest(unittest.TestCase):
    def test(self):

        # Start with a Worker.
        w = Worker()

        # Create some work.
        # For example, take this list...
        x = []

        # And define some work:
        def doSomething():
            x.append(123)
            yield None # has to be a generator!
        w.assign(doSomething())

        # Tell the worker to start working.
        w.work()

        # The work will get done.
        self.assertEquals([123], x)
        
"""
<strong>Now to make it happen.</strong>
"""
# * GeneratorStack

class GeneratorStack(object):
    def __init__(self, task):
        self.stack = []
        self.task = task
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
            next = self.task.next()
        except StopIteration:
            self.pop()
        else:
            if next is None:
                pass # yield None
            else:
                # we can also 'yield genFunc()'
                assert isinstance(next, types.GeneratorType), \
                       "clockwork expects you to yield None or yield a generator function!!"
                self.push(next)

    def stop(self):
        self._done = True
        
    def isDone(self):
        return self._done
   
# * Worker
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
            self.doNextTask()

    def doNextTask(self):
        assert self.queue, "nothing in queue"
        task = self.queue.pop(0)
        task.tick()
        if not task.isDone():
            self.queue.append(task)

  
"""
We will extend this class as we go along.
"""
# * goal: microtheading
"""
Sometimes there's too much work to do at once so
we break the work into small pieces. It would be
great if we could use generators to 'pause' execution
of our task:
"""
class GeneratorTest(unittest.TestCase):
    def test(self):

        # start with an empty list
        data = []

        # and create a generator to append data.
        # generators can be finite:
        def letters():
            data.append("a")
            yield None
            data.append("z")
            yield None

        # or infinite:
        def numbers():
            i = 0
            while True:
                i += 1
                data.append(i)
                yield None

        # assign the generators to the worker
        w = Worker()
        w.assign(letters())
        w.assign(numbers())

        # now run.
        w.doNextTask()
        self.assertEquals(["a"], data)
        w.doNextTask()
        self.assertEquals(["a", 1], data)
        w.doNextTask()
        self.assertEquals(["a", 1, "z"], data)
        w.doNextTask()
        self.assertEquals(["a", 1, "z", 2], data)
        # the next task is to dispose of "letters"
        # so nothing should change in the data:
        w.doNextTask()
        self.assertEquals(["a", 1, "z", 2], data) # same!
        w.doNextTask()
        self.assertEquals(["a", 1, "z", 2, 3], data)
        w.doNextTask()
        self.assertEquals(["a", 1, "z", 2, 3, 4], data)

        
# * implementing generator support
"""
The basic idea here is that generators stay in the queue until they're
done. That means an infinite generator stays int he queue forever, or
at least until someone stops the program.

We still want simple tasks to be removed from the queue immediately
after they are executed, but now we want generators to stick around.
We'll have to modify Worker to make that happen.

Note that we're <strong>defining Worker as a subclass of the earlier
version of Worker.</strong> This is a trick to let us build the class
in stages. It is perfectly legal python syntax, and we will be using
it repeatedly.
"""

# * sleep
"""
sleep waits for (at least) a certain number
of seconds before resuming.
"""
def sleep(secs):
    last = time.time()
    while True:
        now = time.time()
        if (now - last) <= secs:
            yield None
        else:
            break

# * repeat
"""
repeat is a generator for recurring tasks.
Runs the function immediately, then waits
before looping.
"""
def repeat(secs, func):
    while True:
        yield func()
        yield sleep(secs)

# * spawn
"""
spawn a child process in the operating system.
"""
class CommandTest(unittest.TestCase):
    def test(self):
        w = Worker()
        echo = Command(["/bin/echo", "cat"])
        w.assign(echo())
        w.work()
        self.assertEquals("cat\n", echo.stdout.read())
        self.assertEquals("", echo.stderr.read())

class Command(object):
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
       
# * wrap() for non-clockwork callers
"""
Sometimes we want to call clockwork routines from normal python code.

Because of the odd conventions, a clockwork routine only makes sense
inside clockwork, so it can only be called by clockwork-aware
code. But you don't want to cut your features off from all the
non-clockwork code out there, so there has to be a simple way to take
a clockwork routine and wrap it so that it can be used by the outside
world. Well, that's what <code>wrap</code> does.
"""
class WrapTest(unittest.TestCase):
    def test(self):
        # make a clockwork function:
        def routine(data):
            for x in range(4):
                data.append(x*x)
                yield None
                
        # without the wrapper, you get the generator:
        data1 = []
        assert isinstance(routine(data1), types.GeneratorType)
        assert data1 == []
        
        # but the wrapper actually runs it for you:
        data2 = []
        assert wrap(routine(data2)) is None
        self.assertEquals([0,1,4,9], data2)
        
"""
The implementation is just this:
"""
def wrap(gen):
    w = Worker()
    w.assign(gen)
    w.work()

# * return values
"""
As of python2.4, there's no easy way to pass a
value back into a running generator. We could
probably cook up some evil trickery to pass
values around on the generator stack, but since
this problem is likely to go away in python2.5,
we'll just use the simple trick of passing in
a result variable. 

Later, once it's implemented, we'll use use
the new expression form of 'yield':

http://www.python.org/peps/pep-0342.html
"""
class ResultTest(unittest.TestCase):
    def test(self):
        ret = Result()
        ret(5)
        assert ~ret == 5
        ret((1,2,3))
        assert ~ret == (1,2,3)
        
class Result(object):
    def __init__(self):
        self.value = None
    def __call__(self, value):
        self.value = value
    def __invert__(self):
        return self.value


# * @TODO: async sockets
"""
asynchronous sockets are not implemented yet.
when i need to do this, i just leave the http
request to a child process. 
"""


# * spawn, etc..

_mainWorker = Worker()

def spawn(gen):
    return _mainWorker.assign(gen)


def tick():
    _mainWorker.tick()



# * self tests
if __name__=="__main__":
    unittest.main()

# * appendix: competitors
"""
  twisted (yuck)
  http://lgt.berlios.de/#nanothreads
  http://www.python.org/peps/pep-0342.html
"""
