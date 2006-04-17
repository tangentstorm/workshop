"""
<title>Narrative Programming in Python</title>

<p>by <a href='http://withoutane.com/'>Michal J Wallace</a>
   (email:  <em>michal</em> at the domain
            <em>withoutane dot com</em>)</p>

<p>source code: <a href="narrative.py"><code>narrative.py</code></a></p>
"""

# $Id$

import new
import inspect
import unittest

# * Code that Explains Where it Came From
"""
<p>Source code comes with a high learning
curve. Even a clean, well-factored codebase
can be hard to understand, simply because of its size:
with hundreds or thousands of objects and routines,
simply figuring out where to start can be difficult.</p>

<p>The main problem with understanding someone else's
source code is that you weren't there to see it evolve.
No matter how complex the system, it started with a first
line of code, and evolved step by step over time
as the development team added features. To the developers,
this growth was an incremental process, and the knowledge
of how all the pieces fit together accumulated over time.
However, this history is rarely passed on to new developers,
simply because it's not stored anywhere.</p>

<p>Narrative programming is a technique for recording
this history. The code is presented as a narrative,
starting from humble beginnings and evolving the
system over time.</p>

<p>This style is used frequently in books on programming,
but it's rarely seen in production code. Perhaps this is
because this style of programming can be cumbersome
without proper tool support.</p>

<p>However, implementing a narrative programming toolset
in a modern, dynamic language like python is fairly
straightforward, as this program hopes to demonstrate.</p>
"""
# ** Difference Between Narrative and Literate
"""
<p>Narrative programming can be considered a type of <a
href='http://www.literateprogramming.com/'>literate programming</a>,
but there is a major difference. A literate program describes the code
<em>as it is</em>. A narrative program describes <em>how it got to be
that way</em>.</p>

<p>As you will see, <strong>refactoring</strong> plays a large
role in the narrative approach: methods and routines can be added
and redefined through the course of the narrative, so that the
reader watches the code evolve from a simple prototype to
complete system.</p>

<p>Another major difference is the inclusion of <strong>test
cases</strong> in the narrative. While this is certainly
possible with literate code, a test-first style is much more
prominent with the literate approach.</p>
"""
# ** Structure of Narrative Code
"""
<p>The article you are reading right now is an example
of a narrative python program. It written in <strong>pure
python</strong> and does not require a preprocessor for
python to run it. (A separate program converts the python
source to HTML.)</p>

<ul>
<li><strong>narrative</strong>,
    html markup inside python triple-quotes</li>
<li><strong>headlines</strong>,
    consisting of python comments beginning with asterisks</li>
<li>python <strong>unit tests</strong>, and</li>
<li><strong>normal python code</strong></li>
</ul>

<p>If you were looking at the actual python source code for a
narrative program, you would see these elements mixed together
freely. It would look something like this:</p>

<pre>
 # * level 1 headline
 &quot;&quot;&quot;
 narrative
 &quot;&quot;&quot;
 class SomeTest(unittest.TestCase):
     pass
    
 class SomeCode(object):
     pass

 # ** level 2 headline
 moreCode()
</pre>
"""
# ** Emacs Support for Narrative Code
"""
<p>The narrative format plays nice with python and also
with emacs: the special headlines can be used with the
emacs <code>outline-minor-mode</code> to allow folding
(or collapsing) on the headlines.</p>

<p>To use code the folding feature, add this line to
your .emacs file (you'll need <a
href='http://sourceforge.net/projects/python-mode/'>python-mode</a>
first, though):</p>

<code type="elisp"><pre>
(add-hook 'python-mode-hook
	  '(lambda ()
	     (outline-minor-mode)
	     (setq outline-regexp &quot;# [*]+&quot;)))
</code></pre>
"""

# * Decorators for Narrative Programming
"""
<p>The first attempts at a narrative programming system
made use of a preprocessor, but it turned out that python
was flexible enough to allow redefining classes, methods,
and functions over time in one source file. For example,
in the following test case, we replace a method in class
<code>Foo</code> by declaring a new subclass of
<code>Foo</code> that is <em>also called <code>Foo</code></em>.
The second version shadows the first one:</p>
"""

class ShadowMethodExample(unittest.TestCase):
    """
    Demonstrates how to replace replacing a method
    by shadowing a parent class with a subclass.
    """
    def test(self):

        # start with a basic class:
        class Foo(object):
            def bar(self): return "bar"
            def baz(self): return "---"

        assert Foo().bar() == "bar"
        assert Foo().baz() == "---"

        # subclass it with the same name
        class Foo(Foo):

            # and override a method:
            def baz(self): return "baz"

        # it looks like you changed the class:
        assert Foo().bar() == "bar"
        assert Foo().baz() == "baz"

"""
<p>While this approach does work, it's rather clunky, and
you're likely to wind up with a long chain of shadowed
parent classes through the course of your narrative.</p>

<p>Thankfully, the <a
href='http://docs.python.org/lib/module-new.html'><code>new</code></a>
module gives us a way to create new methods on existing classes,
dynamically.</p>

<p>This library uses <code>new</code> behind the scenes,
but hide the details behind a set of convenience
<a href='http://www.python.org/dev/peps/pep-0318/'>decorators</a>
that make the process of writing narrative python code much
cleaner.</p>
"""

# * A Decorator to make Unit Tests
"""
<p>Narrative code makes heavy use of test cases, which are mixed
freely with the implementation. Python comes bundled with a unit
testing framework called <code><a
href='http://docs.python.org/lib/module-unittest.html'>unittest</a></code>,
which allows you to define test cases like this:</p>
"""

class ExampleUnitTest(unittest.TestCase):

    def test_one_plus_one_is_two(self):
        self.assertEquals(1 + 1, 2)
        
    def test_ten_equals_ten(self):
        self.assertEquals(10, 10)

"""
<p>These tests can then be gathered up and run automatically.
(See the <a href='#selftest'>self tests section</a> at the
bottom of this article for an example.)</p>

<p>As you can see, unit tests can contain multiple test
methods. But with a narrative approach, it's much more
convenient to use a bunch of very small tests, and
intersperse those tests with the code that passes them.</p>

<p>Since most narrative tests will have only one test method,
we can save some typing by defining a decorator named
<code>@testcase</code>. It works like this: </p>
"""
class TestCaseTest(unittest.TestCase):
    def test(self):

        # just use the @testcase decorator:
        @testcase
        def myTestCase(test):
            pass

        # ... and your function becomes a TestCase
        assert issubclass(myTestCase, unittest.TestCase)

"""
<p>A decorator is just a function that takes another function
as an argument, and then does something to it. In this case,
our decorator defines a new <code>TestCase</code> subclass
and binds the decorated function to it as a method.</p>

<p>Functions and methods are not quite the same in python,
mostly because of complications from the magical <code>self</code>
parameter. To transform our function into a method, we'll use
the <code>new.instancemethod</code>. We also have to actually
add the method to the new class, which of course is a job
for <code>setattr</code>. The complete decorator looks like
this:</p>
"""
def testcase(f):
    # create a new class:
    class NewTest(unittest.TestCase):
        pass

    # add the test() method
    setattr(NewTest, "test",
            new.instancemethod(f, None, NewTest))

    # and return it
    return NewTest


# * <a name="snapshot">A Decorator to Mark Code as Unfinished</a>
"""
<p>There is one more tool that we'll need before we get
started, and that is a decorator that marks code as
unfinished.</p>

<p>The narrative style allows us to present the history
of an idea in pieces. This can be dangerous (see
<a href='#replaceBad'>@replace Considered Harmful?</a>
in the end notes) but, for rhetorical reasons it's
sometimes useful to present <strong>snapshots</strong>
of the code in progress.</p>

<p>We'll use a decorator called <code>@snapshot</code>
for this purpose. As an extra precaution, we'll make
sure that code marked with this decorator cannot be
run at all (and try out our new <code>@testcase</code>
decorator) with the following test case:</p>
"""

@testcase
def test_snapshot_functions(test):

    # define a function with @snapshot...
    @snapshot
    def work_in_progress():
        pass

    # and it should be tagged as incomplete:
    assert work_in_progress.is_snapshot

    # you shouldn't be able to call it, either:
    test.assertRaises(NotImplementedError, work_in_progress)

@testcase
def test_snapshot_methods(test):

    # define a method with @snapshot...
    class HasSnapshot(object):
        @snapshot
        def work_in_progress(self):
            return "nope"

    # and it should be tagged as incomplete:
    obj  = HasSnapshot()
    assert obj.work_in_progress.is_snapshot

    # you shouldn't be able to call it, either:
    test.assertRaises(NotImplementedError, obj.work_in_progress)



"""
<p>To implement, we can tell our decorator to replace
the function completely:</p>
"""
def snapshot(f):
    def fake_function(*arg, **kw):
        raise NotImplementedError("%s is not finished" % f.__name__)
    fake_function.is_snapshot = True
    return fake_function

"""
<p>Now, on to business.</p>
"""


# * A Decorator to Add A Method
"""
<p>The &quot;add method&quot; decorator is called
<code>@addMethod</code>, and we can define its behavior
with the following unit test:</p>
"""

@testcase
def test_addMethod(self):
    # take an empty class:
    class ExtendMe(object):
        pass

    # add a new method:
    @addMethod(ExtendMe)
    def doSomething(self, aNumber):
        return aNumber + 1

    # and test that it works:
    e = ExtendMe()
    assert e.doSomething(1) == 2

"""
<p>The code for <code>@addMethod</code> looks a lot like
the code for <code>@testcase</code>, with one difference:
instead of binding the function to a new class, we're going
to specify the class as a parameter.</p>

<p>Decorators that take parameters have to return a wrapper
function, and that wrapper is what does the actual decorating.
(See <a href='http://www.python.org/dev/peps/pep-0318/#current-syntax'>PEP
318</a> for details.) The end result looks like this:</p>
"""

@snapshot
def addMethod(theClass):
    """
    A decorator that adds a new method to a class.
    """
    def wrapper(f):
        setattr(theClass, f.__name__,
                new.instancemethod(f, None, theClass))
    return wrapper

"""
<p>Notice the use of <code>@snapshot</code>? A clear signal
that we're not quite done with <code>addMethod</code>.</p>
"""


# * Adding vs Replacing
"""
<p>The way it's defined now, @addMethod works just
as well for <em>replacing</em> a method that's
already there. Python doesn't care.</p>

<p>However, if you're going to scatter methods
throughout a program, it makes sense to help the
reader distinguish between new and updated
methods.</p>

<p>Narrative-aware tools might also treat the two
cases differently. For example, it would be nice to
show not only that the method has changed, but also
<em>how</em> it has changed, perhaps by showing a
color-coded, line-by-line <code>diff</code>.</p>

<p>In any case, <code>@replaceMethod()</code>
works like this:</p>
"""

@testcase
def test_replaceMethod(test):

    # take a class with a method
    class UpdateMe(object):
        @snapshot
        def unfinished(self):
            return "you can replace me"

    up = UpdateMe()
    test.assertRaises(NotImplementedError, up.unfinished)

    # use the replaceMethod() decorator
    @replaceMethod(UpdateMe)
    def unfinished(self):
        return "all done"

    # and the class (and all instances) get the new method!
    assert up.unfinished() == "all done" 
    assert UpdateMe().unfinished() == "all done"


@testcase
def test_replaceMethod_non_snapshot(test):

    # but if you don't use @snapshot first:
    class CantUpdateMe(object):
        def finished(self):
            return "you can't replace me"

    # then you can't replace the method:
    try:
        @replaceMethod(CantUpdateMe)
        def finished(self):
            pass
    except TypeError:
        pass
    else:
        test.fail("should have failed on replacing finished routine")

@testcase
def test_replaceMethod_undefined(self):

    # when you take a class with no methods...
    class Blank(object):
        pass

    try:
        # and you try to 'replace' a method on it...
        @replaceMethod(Blank)
        def aNewMethod(self):
            pass
    except NameError:

        # then you get an error.
        pass
    else:
        self.fail("should have raised NameError on undefined method")

"""
<p>The implementation looks like this:</p>
"""
def replaceMethod(theClass):
    def wrapper(f):
        orig = theClass.__dict__.get(f.__name__, None)

        if not orig:
            raise NameError("attempt to replace nonexistent method %s.%s!"
                            % (theClass.__name__, f.__name__))

        if not getattr(orig, "is_snapshot", None):
            raise TypeError("attempt to replace non-@snapshot method %s.%s"
                            % (theClass.__name__, f.__name__))
        
        setattr(theClass, f.__name__,
                new.instancemethod(f, None, theClass))
        
    return wrapper



# * Replacing a Function
"""
<p>Again, python lets you functions methods without any
special syntax whatsoever. You just define a new
function with the same name. The <code>@replace</code>
decorator simply makes this intent explicit.</p>
"""

@testcase
def test_replace(test):
        
    def replaceMe():
        return "original"

    @replace
    def replaceMe():
        return "modified"

    assert replaceMe() == "modified"


"""
<p>Once again, we'll add a test to make sure you
can't replace something that isn't there:</p>
"""

@testcase
def test_replace_undefined(test):
    try:
        @replace
        def notDefinedYet():
            pass
    except NameError:
        pass
    else:
        test.fail("should have gotten NameError")
                

"""
<p>Now, in order for our decorator to determine whether
a function with the same name already exists, we need
to inspect the stack. Not surprisingly, this is done
with a call to  <a
href='http://python.org/doc/lib/inspect-stack.html'>inspect.stack</a></p>

<p>Once we make the check, there's nothing else to do,
except to return the new function as-is.</p>
"""

def replace(f):
    
    # grab the callling context's local dictionary off the stack
    calling_context = inspect.stack()[1][0].f_locals # ick :)

    # and make sure the function already exists
    if not calling_context.has_key(f.__name__):
        raise NameError("can't replace nonexistent function %s" % f.__name__)

    # python handles the rest:
    return f



# * <a name="already">Using @addMethod on a Method That's Already There</a>
"""
<p>Let's try out our new <code>@replace</code> decorator by
replacing <code>@addMethod</code> with a version that checks
whether the method already exists. Here's the test case:</p>
"""

@testcase
def test_addMethod_already_there(self):

    # take a class with a method
    class AlreadyThere(object):
        def meth(self): pass

    try:
        # try to add that same method
        @addMethod(AlreadyThere)
        def meth(self):
            pass
    except NameError:
        # ... and you should get an error.
        pass
    else:
        self.fail("should have raised NameError for pre-existing function")

"""
<p>The change to make this work is simple:</p>
"""

@replace
def addMethod(theClass):
    """
    A decorator that adds a new method to a class.
    """
    def wrapper(f):
        if (theClass.__dict__.get(f.__name__)):
            raise NameError("class %s already has method named %s" 
                            % (theClass.__name__, f.__name__))
        setattr(theClass, f.__name__,
                new.instancemethod(f, None, theClass))
    return wrapper



"""
<p>Note the lack of a <code>@snapshot</code> decorator:
this is the final version of <code>@addMethod</code>. And
in fact, with that change, the <code>narrative</code>
module is complete.</p>
"""


# * Rewriting History: Thoughts on the Narrative Style
"""
<p>Now that the code is out of the way, I'd like to
take a few minutes to write about the <em>experience</em>
of writing software this way.</p>

<p>I think it's interesting that the order in which
I originally wrote the decorators is not the order
in which they're presented. In particular, I created
<code>@testcase</code> as an afterthought, and it
originally appeared at the end of the file. When I
came back to rewrite the text, and saw that it was
simpler than the other decorators, I moved it to
the front.</p>

<p>Similarly, the first draft didn't make use of
<code>@replace</code>. I wrote <code>@addMethod</code>
and <code>@replaceMethod</code> in their final forms,
with the existence-checks already in place. In the
rewrite stage, I rearranged the tests, and (using
copy and paste) created the simplified versions that
appear first in the narrative.</p>
"""
# * <a name="replaceBad"><code>@replace</code> Considered Harmful?</a>
"""
<p>However, if you're anything like me, the phrase <em>copy
and paste</em>, when applied to programming, raises a huge
red flag. Does that mean <code>@replace</code> and
<code>@replaceMethod</code> should be avoided?</p>

<p>It's said that good software should be <em>open for
extension</em> but <em>closed for modification</em> - what's
known as the <a
href='http://www.c2.com/cgi/wiki?OpenClosedPrinciple'>Open-Closed
Principle</a>.</p>

<p>The <code>@addMethod</code> decorator is a good
example of a nice extension mechanism. It doesn't break
existing code, it doesn't require cutting and pasting,
and it doesn't result in duplication. The main benefit
is that it allows you to intersperse headlines, text, and
test cases between your methods, so that readers get
the feel of incremental development.</p>

<p>The <code>@replace</code> and <code>@replaceMethod</code>
decorators are different beasts. The main concern for me is
that even with <code>@snapshot</code>, there is a possibility
that a hurried maintainer would edit the wrong version of
the code.</p>

<p>However, two things guard against this. First, there are
the test cases. The narrative and test-first approaches are
complementary. Changes made to a snapshot would be cancelled
out by the calls to <code>@replaceMethod</code> later in the
file. The errant maintainers might disrupt the narrative flow,
but would have no affect whatsoever on the system's actual
behavior. If they wrote their own test cases, they'd soon
discover why their changes had no effect, and if they didn't,
well... Serves them right. :)</p>

<p>The second mitigating circumstance is the narrative itself.
Because a sort of history is imposed on the code, it becomes
important when making changes to think through not only <em>what</em>
needs to change, but <em>when</em> to change it. This might seem
difficult or daunting, but we humans are natural planners, and
thinking of the software as a plan is actually quite natural.</p>

<p>However, the <code>replace</code> style can often be
avoided, because the narrative style allows you to change
history...</p>

"""

# * Pros and Cons of Time Travel
"""
<p>There is a danger that the most natural place to implement
a change is early in the narrative's timeline: that is, had you
done something differently early on, things would be easier now.</p>

<p>If every change between the old point and the new is an
addition, then going &quot;back in time&quot; and changing
things &quot;early on&quot; is probably not too difficult.
But if there are multiple snapshots of the code in question,
then introducing a change at the beginning would force you
to update all of them, as the effects of your changes
propagate through the rest of the narrative.</p>

<p>Granted, snapshot code never actually runs, so python
doesn't care if your narrative doesn't flow naturally. You
can delete the snapshots entirely and things will still work.
But the whole premise behind narrative programming is the idea
that preserving history for future developers pays off. </p>

<p>Therefore, it is often sensible to refactor the current
version of the code before writing its replacement. It is
perfectly okay for the narrative to introduce code that is
far more flexible and powerful than required by the test cases
that precede it. To readers encountering the system for the
first time, some choices might seem like overengineering or
violations of the <a title=\"You Aren't Gonna Need It\"
   href='http://xp.c2.com/YouArentGonnaNeedIt.html'>YAGNI
principle</a>, but that is because they are encountering
the situation without the benefit of hindsight.</p>

<p>Of course, since the &quot;future&quot; of the narrative
is just another piece of text, it's also totally permissible
to pass on a bit of future knowledge through foreshadowing,
possibly with a link to a description of the future problem.</p>

<p>For example, <code>@snapshot</code> was the last thing I
implemented, but because the final versions of <code>@replace</code>
and <code>@replaceMethod</code> only work on snapshots, and
because I wanted to introduce <code>@addMethod</code> as a
simplified version without the <a href='#already'>extra
test logic</a>, <code>@snapshot</code> had to be defined
before <code>@addMethod</code>. So put <a href='#snapshot'>the
@snapshot stuff</a> up front, with a note that we'd need it
later and a link to this extended post-code discussion.</p>

<p>In a sense, the narrative style isn't meant to present
the literal history of a project, but rather some
<em>plausible</em> history. It is rather like blazing a
trail for others to follow once you already know where
you're going.</p>
"""
    

# * <a name="selftest">Appendix: Self-Tests For This Code</a>
"""
<p>Python makes it easy to run all the tests defined
in this narrative. It boils down to this: </p>
"""
if __name__=="__main__":
    unittest.main()
    
