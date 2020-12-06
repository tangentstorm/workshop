#!/bin/env python
import unittest
from narrative import testcase
from clockwork import *

# * clockwork: simple asynchronous programming
# **    background
"""

<p>Clockwork is a sub-language embedded in python for writing
asynchronous microthreaded programs.</p>

<p>This can be used to simplify the flow of control in event driven
environments such as GUIs, and also provides for lightweight
concurrency without (some) of the pitfalls of traditional threads.</p>

<p>The clockwork language is defined through extending the
python <code>yield</code> keyword. Microthreads are simply
normal generators that follow special conventions.</p>

<p>All non-blocking code is implemented as a generator.
You can call any normal python function, but these functions
block the flow of execution until they complete. For many
cases, this is fine, but if you want to create a non-blocking
function that returns a single value, you must implement it
as a generator. However, python's normal <code>return</code>
keyword is not allowed inside a generator. We could simply
have a single <code>yield</code> statement, but this makes
it hard to distinguish a generator that generates a sequence
of length one (and may invoke some other side effects before
StopIteration is raised) from a generator that 'returns' one
item and stops execution.</p>

<p>By defining a set of 'keyword objects', we can extend the
<code>yield</code> keyword to distinguish between returning
a value and generating a series of one item, and create a
variety of other interesting behaviors as well.</p>

<p>The keywords defined to date are:</p>

<ul>
<li><b>yield Control</b>
    pauses execution temporarily so other microthreads can run</li>
<li><b>yield Sub(gen)</b>
    passes control to a sub-generator. Sub may yield Return a value.</li>
<li><b>yield Return(...)</b>
    returns a value like a regular python functions</li>
<li><b>yield Value(...)</b>
    yields a value (just like regular python generators)</li>
<li><b>yield Input(...)</b>
    waits for input (asynchronously) from the user.</li>
<li><b>yield Call(gen)</b>
    performs a <em>tail call</em> - replacing the current
    microthread with the one in <code>gen</code></li>
<li><b>yield CallCC(gen)</b>
    like Call, but also sends the current continuation
    of this microthread the first message passed to
    the new generator (so that it can be invoked
    later with Call, Sub, or CallCC
    </li>
<li>-----</li>
<li><b>yield Each(series)</b>
    yields each item in a series
    same effect as <code>[(yield each) for each in series]</code> 
    </li>
</ul>



Usage:

<pre>
w = Worker()
w.assign(yourGenerator)

# and then...

if in_loop:
    w.tick()
else:
    w.work()
</pre>

"""

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
            yield Control # has to be a generator!
        w.assign(doSomething())

        # Tell the worker to start working.
        w.work()

        # The work will get done.
        self.assertEquals([123], x)
        
# * Pause execution with yield Control
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
            yield Control
            data.append("z")
            yield Control

        # or infinite:
        def numbers():
            i = 0
            while True:
                i += 1
                data.append(i)
                yield Control

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

        
# * asynchronous generators with yield Value
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

class CommandTest(unittest.TestCase):
    def test(self):
        w = Worker()
        echo = Command(["echo", "cat"]) # will work on any major OS
        w.assign(echo())
        w.work()
        self.assertEquals("cat\n", echo.stdout.read())
        self.assertEquals("", echo.stderr.read())


# * Call from outside clockwork wyth wrap() 
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
                yield Control
                
        # without the wrapper, you get the generator:
        data1 = []
        assert isinstance(routine(data1), types.GeneratorType)
        assert data1 == []
        
        # but the wrapper actually runs it for you:
        data2 = []
        assert wrap(routine(data2)) is None
        self.assertEquals([0,1,4,9], data2)


# * flattening nested generators
"""
Suppose we want to use nested generators, but
our calling context requires a normal generator.

For example, in scarlet, we often want to use
nesting inside a wsgi generator.

The flatten() routine does this for us.
"""
@testcase
def FlattenTest(self):

    def top():
        yield 1
        yield kid() #@TODO: Each
        yield 3

    def kid():
        yield 2

    self.assertEquals([1,2,3], list(flatten(top())))


# * standalone generators
"""
You may need multiple, parameterized instances
of a generator stack to behave like normal
generator functions.

For example, WSGI takes a generator function
rather than the actual generator object
because it needs to pass in the http_start
and environ parameters for each instance.

You can use the @clockwork.standalone
feature to make this happen.


@TODO: that makes no sense, and this test passes even without @encapsulate

"""
@testcase
def StandaloneTest(self):

    def repeat(num):
        for n in range(num):
            yield None  # get filtered out because it's not in a Value()
            yield Value(num)

    @standalone
    def gen(*args):
        for a in reversed(args):
            yield repeat(a)

    self.assertEquals([3,3,3,2,2,1], list(gen(1,2,3)))


# * return values
class ReturnTest(unittest.TestCase):
    """
    What if we want a single async return value?
    For example, we might want to do an expensive task
    out of process, wait for it to finish, and return
    the result, but never block. So we want:
    yield Control
    yield Control
    yield Return(value)
    (for a specific example, see procwork.py)
    """
    def test_async(self):
        def do_async(x):
            yield Control
            if x == 0:
                yield Return('')
            else:
                yield Return('x' + (yield do_async(x-1)))
                
        self.assertEquals('', wrap(do_async(0)))
        self.assertEquals('x', wrap(do_async(1)))
        self.assertEquals('xxx', wrap(do_async(3)))

# * yielding values
@testcase
def YieldValuesTest(self):
    """
    We may also want to emulate the normal yield statement
    and yield multiple values. So we need a wrapper that
    tells clockwork to let those values escape.

    Note that we have to use 'genwrap' rather than 'wrap'
    because wrap behaves like a function.
    """
    def values(x):
        yield Value(x+1)
        yield Control
        yield Value(x+2)
        yield Value(x+3)

    self.assertEquals([11, 12, 13],
                      list(genwrap(values(10))))

        
# * inter-task communication using Value and send()
@testcase
def ValueAndSendTest(self):

    def hello():
        name = yield Value("what is your name?")
        yield Control # just to show it's clockwork
        yield Value("hello, %s" % name)

    w = genwrap(hello())
    self.assertEquals(w.next(), "what is your name?")
    self.assertEquals(w.send('fred'), "hello, fred")


# * real input/output with Input and Output
@testcase
def InputOutputTest(self):
    """
    This test is almost exactly the same as above except
    it uses Input/Output objects.

    These work similarly at the top level:
    """
    def interactive():
        name = yield Input("what is your name?", str)
        yield Control # just to show it's clockwork
        yield Output("hello, %s" % name)

    w = genwrap(interactive())
    i = w.next(); assert isinstance(i, Input)
    i.send("Mr. Jones")
    self.assertEquals(w.next(), Output("hello, Mr. Jones"))

    """
    but also work from deep within a call stack:
    """ 
    def nested():
        yield interactive()
        
    w = genwrap(nested())
    i = w.next(); assert isinstance(i, Input)
    i.send("Mr. Smith")
    self.assertEquals(w.next(), Output("hello, Mr. Smith"))


# * @TODO: async sockets
"""
asynchronous sockets are not implemented yet.
when i need to do this, i just leave the http
request to a child process. 
"""

# * appendix: competitors/related modules
"""
  twisted (yuck)
  http://lgt.berlios.de/#nanothreads
  http://www.python.org/peps/pep-0342.html
"""


# * self tests
if __name__=="__main__":
    unittest.main()

