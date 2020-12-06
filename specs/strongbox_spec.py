#!/usr/bin/env python2.5
import narrative as narr
import unittest, re
from strongbox import *
"""
<title>strongbox: powerful data classes for python</title>
"""
# * Overview
"""
<p><strong>Classes that inherit from
<code>strongbox.StrongBox</code></strong>:</p>

<ul>
<li><strong>define their attributes</strong> with
    <code>attr</code>, <code>link</code>, and <code>linkset</code></li>
<li>provide <strong>type and value checking</strong> for those attributes</li>
<li>allow easy declaration of <strong>getter and setter</strong> methods</li>
<li>are <strong>observable</strong>, so they can
  <strong>notify observers</strong> of updates</li>
<li>are <strong>injectable</strong>, for
  <strong>lazy loading</strong> from storage</li>
</ul>

<p><strong>This document</strong> is a <strong>narrative
python</strong> program and thus a <strong>formatted version</strong>
of the actual <a href='strongbox.py'>strongbox.py</a> source code and 
and test cases.</p>
"""
# * - specification -
"""
<p>The classes in the previous section will be <strong>extended
dynamically</strong> throughout this document.</p>

<p>The narrative takes the form of an <strong>executable
specification</strong>. The <strong>headlines</strong> generally
indicate <strong>features</strong>, and are usually followed by a few
sentences of <strong>discussion</strong>, followed by a <strong>unit
test</strong> that shows the intent explicitly. The actual
<strong>code is in the second half</strong> of this document.</p>

<p>Okay! Let's get started.</p>
"""

# * Storing Private Data with <code>Strict</code>
"""
<p>All <code>Strict</code> instances should have a
<code>.private</code> namespace, which lets them store private
variables explicitly. It works like this:</p>
"""
@narr.testcase
def test_private(self):
    s = Strict()
    assert hasattr(s, "private")
    s.private.c = 1
    assert s.private.c == 1
    assert getattr(s, "c", None) is None

"""
<p>The <strong><code>testcase</code> decorator</strong> turns the
above code into a standard <code>unittest.TestCase</code>. All of
these test cases can be checked simply by executing this module
in the python interpreter.</p>
"""

# * Declaring Attributes with <code>StrongBox</code> and <code>attr</code>
# ** 
"""
<p>Attributes allow you define up front which properties your
<code>StrongBox</code> class will support. You can create
attributes with the <code>attr</code> constructor.</p>
"""
# ** <code>attr</code> Only Works on <code>StrongBox</code> Classes
"""
<p>Let's start with the basics. To use <code>attr</code>, you need
to <strong>subclass <code>StrongBox</code></strong>.</p>

<p class='aside'>Actually, <code>BlackBox</code> will work too if you
don't need injectors or observers, but <strong><code>attr</code>
doesn't work with normal classes</strong>. This is because
<code>MetaBox</code> has special logic to <strong>tell each
<code>attr</code> its name</strong>.  If an <code>attr</code> doesn't
know its name, it can't call <code>setattr</code> on
<code>.private</code>.</p>

<p>The class declaration should include <strong>all valid
attributes</strong> for that class. No undeclared attributes can be
accessed on class instances. Attributes are also
<strong>inherited</strong> from parent classes.</p>

<p>In this the following test case, the <code>Person</code> class
contains one attribute, called <code>name</code>.</p>
"""

@narr.testcase
def test_attr_must_be_declared(test):

    # every Person has a name
    class Person(StrongBox): 
        name = attr(str)

    # fred is a Person, so he must have a .name
    fred = Person()
    fred.name = "fred"
    assert fred.name == "fred"
    
    # but setting or getting .age fails because it was not declared
    test.assertRaises(AttributeError, setattr, fred, "age", 50)
    test.assertRaises(AttributeError, getattr, fred, "age")
    
# ** Declaring Default Values
# *** 
"""
<p>You can declare a default value for an attribute by passing the
keyword <strong><code>default</code></strong> to
<code>attr</code>.</p>
"""
@narr.testcase    
def test_defaults(self):

    # Foo.bar is an int that defaults to 5
    class Foo(BlackBox):
        bar = attr(int, default=5)
        
    foo = Foo()
    assert foo.bar == 5
    
# *** Default Defaults
"""
<p>If a default value is not given, a <em>default</em> default
is used, based on the type:</p>

<ul>
<li><strong>strings</strong> default to <strong>''</strong> (empty)</li>
<li><strong>numbers</strong> default to <strong>0</strong></li>
<li><strong>other types</strong> default to
    <strong><code>None</code></strong></li>
</ul>
"""
@narr.testcase
def test_default_defaults(self):
    class Foo(BlackBox):
        aStr = attr(str)
        anInt = attr(int)
        aLong = attr(float)
        aFloat = attr(float)
        aList = attr(list)
        
    foo = Foo()
    assert foo.aStr == ''
    assert foo.anInt == 0
    assert foo.aLong == 0
    assert foo.aFloat == 0
    assert foo.aList == None # not []!!!
    
    
# *** Defaults are Cast to the Attribute's Type
"""
<p>Explicit defaults act as arguments to the
<strong>attribute type's constructor</strong>.</p>
"""
@narr.testcase
def test_othertypes(test):
 
    # take a class that wraps a string but is NOT a string
    class UpCase:
        def __init__(self, value):
            self.value = str(value).upper()
        def __cmp__(self, other):
            return cmp(self.value, other)

    # declare non-string attributes with string defaults
    class Foo(BlackBox):
        upper = attr(UpCase, default="xyz")
        num = attr(int, default="123")
    foo = Foo()
    
    # the default strings are cast to the appropriate types
    assert isinstance(foo.upper, UpCase)
    test.assertEquals("XYZ", foo.upper)
    test.assertEquals(123, foo.num)

    
# ** Setting Multiple Attributes
# *** in the constructor
"""
<p>You can also set initial attribute values on a
<strong>per-instance</strong> basis passing them in through the
<strong><code>Strongbox</code> constructor</strong>:
"""
@narr.testcase    
def test_constructor(self):

    # Foo.bar defaults to 5
    class Foo(StrongBox):
        bar = attr(int, default=5)

    # but the constructor wins:
    foo = Foo(bar=12)
    assert foo.bar == 12


# *** <code>update()</code> and <code>noisyUpdate()</code>
"""
<p>You can also do batch updates later. <code>Strongbox.update</code>
takes <strong>keyword arguments</strong>, just like the constructor:</p>
"""
@narr.testcase
def test_noisyUpdate(test):
    class Foo(BlackBox):
        a = attr(int)
        b = attr(int)

    f = Foo()
    f.noisyUpdate(a=1, b=2, c=3, d=4)
    assert f.a == 1
    assert f.b == 2

    # or pass in a dict with **
    f.noisyUpdate(**{"b": 5})
    assert f.b == 5


# ** Attributes Enforce their Types
# *** 
"""
<p>When you assign a value to one of your attributes, the
attribute <strong>checks its type</strong>. Each attribute
is associated with exactly <strong>one</strong> type.</p>
"""
# *** Type Casting
"""
<p>When confronted with a value of another type, an attribute will
<strong>attempt to cast the value</strong> to the desired type.</p>
"""
@narr.testcase
def test_attr_casting(test):

    # a Person has a name and an age
    class Person(StrongBox):
        name = attr(str)
        age = attr(int)

    # using the declared types is easy
    fred = Person()
    fred.name = "Fred"
    assert fred.name == "Fred"
    fred.age = 72
    assert fred.age == 72


    # attr(str) turns values into strings...
    fred.name = 123
    assert fred.name != 123
    assert fred.name == "123"

    # attr(int) turns values into ints, and so on.
    fred.age = "123"
    assert fred.age != "123"
    assert fred.age == 123

   
# *** Type Errors
"""
<p>If the type cast fails, a <strong><code>TypeError</code> is
thrown</strong></p>
"""
@narr.testcase
def test_static_typing(test):

    # Foo.bar is an int
    class Foo(BlackBox):
       bar = attr(int)
    foo = Foo()

    # should get TypeError tyring to assign a string 
    test.assertRaises(TypeError, setattr, foo.bar, "non-int value")

# ** Dealing with <code>None</code>
"""
<p>Attributes <strong>allow <code>None</code> by default</strong>
but you can toggle this with the <code>allowNone</code> parameter</p>
"""

@narr.testcase
def test_allowNone(self):
    """
    We can disallow None if we want.
    """
    class Foo(BlackBox):
        bar = attr(int, allowNone=False)
        baz = attr(int) 
    foo = Foo(bar=11, baz=22)

    self.assertRaises(ValueError, setattr, foo, "bar", None)
    foo.baz = None # allowNone=True by default
    
# ** Empty strings convert to None
"""
<p>This is a <strong>special case</strong> for web pages.
If a form field on an HTML form is left blank, some browsers
(IE5, possibly all of them) will send an empty string for
that field.</p>

<p>If casting the empty string fails, the attribute will
attempt to use None instead.</p>
"""

@narr.testcase
def test_emptyString(self):
    
    class X:
        pass
    
    class Foo(BlackBox):
        i = attr(int)
        s = attr(str)
        d = attr(X)
        
    f = Foo()
    f.i = ""; self.assertEquals(None, f.i)
    f.s = ""; assert f.s == ""
    f.d = ""; assert f.d is None
    

# ** Define Validators with <code>okay=xxx</code>
# *** 
"""
<p>In addition to checking an assigned object's type, attributes
can check its <strong>value</strong>. This is done through the
<strong><code>okay</code> keyword</strong> argument. There are
three kinds of <strong><code>okay</code> value specifiers</strong>:</p>

<ul>
<li>a <strong>string</strong>
    containing a <strong>regular expression</strong></li>
<li>a <strong>list</strong>
    containing <strong>all acceptible values</strong></li>
<li>a <strong>function or <code>lambda</code></strong>
    that returns <code>True</code> or <code>False</code>
    (valid or not valid) based on its parameter</li>
</ul>

<p>A validator <strong>raises <code>ValueError</code></strong>
if it fails to match.</p>
"""
# *** regular expression validators
"""
<p>These should probably only be used with attr(str)</p>
"""
@narr.testcase
def test_okay_regexp(test):
    class UsCitizen(BlackBox):
        ssn = attr(str, okay=r"\d{3}-?\d{2}-?\d{4}")

    elmer = UsCitizen()
    
    # correctly formatted social security numbers work:
    elmer.ssn = "404-44-4040" # should work

    # but phone numbers (even famous ones) will fail:
    test.assertRaises(ValueError, setattr, elmer, "ssn", "867-5309")
    
# *** list validators
"""
<p>List validators are handy for generating dropdowns
automatically. They're a good match for <code>enum</code>
rows in a SQL database.</p>
"""
@narr.testcase
def test_okay_list(test):

    # this paint comes in only three colors
    class Paint(BlackBox):
        color = attr(str, okay=["red", "green", "blue"])

    p = Paint()
    p.color = "red" # should work

    # p.color = "orange" should fail:
    test.assertRaises(ValueError, setattr, p, "color", "orange")

    # you can get the .okay value at runtime from Paint.color
    assert Paint.color.okay == ["red", "green", "blue"]
    
# *** function validators
"""
<p>You can add any validator you want by passing in a function
or lambda. Your validator <strong>should take one value</strong>:
the object being validated.</p>
"""
@narr.testcase
def test_okay_lambda(test):

    # lambda validator only accepts value between 5 and 10
    class Foo(BlackBox):
        bar = attr(int, okay=lambda x: 5 < x < 10)
        
    foo = Foo()
    foo.bar = 7 # should work
    test.assertRaises(ValueError, setattr, foo, "bar", 10)
    
    

# * Accessors
"""
<p>Methods named <strong><code>get_xxx</code> and
<code>set_xxx</code></strong> are magically understood to
be accessors for attribute <code>xxx</code>.</p>

<p>There is <strong><code>no del_xxx</code></strong>
because attributes cannot be added or removed once
the class is created.</p>

<p>All properties have getters and setters, even if
you don't define them yourself.</p>
"""
@narr.testcase
def test_calculated_fields(test):
    class Foo(StrongBox):        
        def get_x(self):
            return 5

    f = Foo()
    assert f.x == 5
    assert f.getSlots()[0][0]=="x"

@narr.testcase
def test_custom_getter(test):
    class Foo(StrongBox):
        counter = attr(int)
        def get_counter(self):
            self.private.counter += 1
            return self.private.counter
    f = Foo()
    assert f.counter == 1
    assert f.counter == 2
    assert f.counter == 3
    f.counter = 0
    assert f.counter == 1
    

"""
You can even have virtual members that aren't actually
stored, for example:
"""
try:
    from crypt import crypt
except ImportError:
    from md5crypt import unix_md5_crypt as crypt
    
@narr.testcase
def test_setter(test):
    class User(Strongbox):
        cryptpwd = attr(str, default='')

        def set_password(self, value):
            self.cryptpwd = crypt.crypt(value, 'salt')

        def get_password(self):
            raise AttributeError("User.password is read only!")

    u = User()
    assert u.cryptpwd == ''
    u.password = 'whatever'
    assert u.cryptpwd == 'saYgjMavvoiII'



# * Defining Relationships Between Data Classes
# ** <code>link</code>
# **** 
@narr.testcase
def test_simple(self):
    class Child(StrongBox):
        name = attr(str)
    class Parent(StrongBox):
        kid = link(Child)
    p = Parent()
    p.kid = Child(name="damien")
    
# **** links are type-safe
@narr.testcase
def test_typing(self):
    class LinkedListMember(StrongBox):
        next = link(lambda : LinkedListMember)

    class NonMember(StrongBox):
        pass

    class NotEvenAStrongBox:
        pass

    one = LinkedListMember()
    two = LinkedListMember()
    bad = NonMember()

    one.next = two
    two.next = one
    assert one.next.next is one

    failed = 0
    for item in (bad, NotEvenAStrongBox(), "wrong type"):
        try:
            one.next = item
        except TypeError:
            failed += 1
    assert failed == 3, "Link should force types"

    two = LinkedListMember()
    one = LinkedListMember(next=two)
    assert one.next is two
    assert two.next is None
# ** <code>linkset</code>
# **** add to the set with <code>&lt;&lt;</code>
"""
<p>Use <code>&lt;&lt;</code> to append to a linkset.</p>
"""
@narr.testcase
def test_simple_linkset(self):

    class Child(StrongBox):
        mama = link(lambda : Parent)
        name = attr(str)
    class Parent(StrongBox):
        kids = linkset(Child, "mama")

    p = Parent()
    c = Child(name="freddie jr")
    p.kids << c
    assert p.kids[0] is c
    assert c.mama is p
# **** linksets are also type-safe
@narr.testcase
def test_typing(self):


    class Node(StrongBox):
        kids = linkset(lambda : Node, None)


    class NonNode:
        pass

    top = Node()
    assert top.kids == [], str(top.kids)

    try:
        top.kids = []
        gotError = 0
    except AttributeError:
        gotError = 1
    assert gotError, "should get error assigning to linkset."

    kidA = Node()
    kidB = Node()

    # I like this syntax better for append...
    top.kids << kidA
    top.kids << kidB
    assert len(top.kids) == 2
    assert top.kids[1] == kidB

    self.assertRaises(TypeError, top.kids.append, NonNode())
    self.assertRaises(TypeError, top.kids.__lshift__, NonNode())

    
            
# ** Use <code>lambda</code> for Forward Declarations
"""
<p>Any attribute can wrap its type in a
<strong>no-argument <code>lambda</code></strong>,
but this really only comes in handy for <code>link</code> and
<code>linkset</code>. 
"""
@narr.testcase
def test_forward_links(test):
    
    # This class links to itself
    class Linked(StrongBox):
        # "Linked" isn't finished yet, so use lambda:
        next = link(lambda : Linked)

    chain = Linked()
    chain.next = Linked()
    chain.next.next = Linked()

    # once you assign one, the lambda disappears:
    assert Linked.next.type == Linked
        
   
    
# * Attributes are Inheritable
"""
<p>Attributes are passed down to subclasses, just like normal
properties.</p>
"""
@narr.testcase
def test_inheritance(self):
    # Dad class has a .nose:
    class Dad(BlackBox):
        nose = attr(str, default="big")
        
    # Son class inherits it:
    class Son(Dad):
        pass
    assert Son().nose == "big"
    
# * introspection support  
# ** getSlots, getSlotsOfType
"""
<p>These methods return a list of name, <code>attr</code> pairs.</p>
"""
@narr.testcase
def test_getSlots(test):
    class Fee(StrongBox):
        x = attr(str)
    class Foo(StrongBox):
        a = attr(str)
        b = attr(int)
        c = link(Fee)

    foo = Foo()
    test.assertEquals([("a", Foo.a), ("b", Foo.b), ("c", Foo.c)],
                      list(foo.getSlots()))
    test.assertEquals([("c", Foo.c)], list(foo.getSlotsOfType(link)))


# ** listWritableSlots
"""
<p>Sometimes, you want to cache calculated fields (get_xxx without
a set_xxx) in a database. If an object-relational mapper such as
the clerks module wants to load data from columns back into
the corresponding attributes, there needs to be a way to stop
it from trying to load data into these calculated fields. We
can provide such a service through .getWritableSlots</p>
"""
@narr.testcase
def test_listWritableSlots(test):
    class Foo(StrongBox):
        a = attr(str)
        b = attr(int)
        c = link(lambda: Foo)

    def get_d(self): # readable only
        return 2

    #@TODCO: handle setters

    foo = Foo()
    test.assertEquals(["a", "b", "c"],
                      foo.listWritableSlots())

# ** attributeValues
"""
<p>The attributeValues() method returns a dict.</p>
"""
@narr.testcase
def test_attributeValues(test):
    class Other(StrongBox):
        x = attr(int)
    class Valuable(StrongBox):
        a = attr(str)
        b = attr(int)
        c = link(Other)

    v = Valuable(a="asdf", b=5)
    test.assertEquals({"a":"asdf", "b":5}, v.attributeValues())


# ** repr()
@narr.testcase
def test_repr(test):
    class Other(StrongBox):
        x = attr(int)
    class Valuable(StrongBox):
        a = attr(str)
        b = attr(int)
        c = link(Other)

    v = Valuable(a="asdf", b=5)
    r = repr(v)

    assert r.startswith("Valuable(")
    assert r.count("a='asdf'")
    assert not r.count("c=")
    assert r.endswith(")")
    
    
# * Observable
"""
<p>We implement the famous Gang of Four Observer pattern:</p>
"""
@narr.testcase
def test_Observable(self):
    subject = StrongBox()
    observer = object()
    subject.addObserver(observer)
    assert observer in subject.private.observers
    subject.removeObserver(observer)
    assert observer not in subject.private.observers

@narr.testcase
def test_set_event(self):
    class Observer:
        def __init__(self):
            self.updated = False
        def update(self, subject, name, value):
            self.updated = True
            self.name = name
            self.value = value
    class Subject(StrongBox):
        name = attr(str)

    # first, try with no observers:
    sub = Subject()
    sub.name='wilbur'
    assert sub.name=='wilbur', sub.name

    # now add an observer:
    obs = Observer()
    assert not obs.updated
    sub.addObserver(obs.update)
    sub.name = "fred"
    assert obs.updated, "observer should have been updated on setattr"
    assert obs.name == "name"
    assert obs.value == "fred"
    
# * Injectable
"""
<p>Injectable is like Observable, but instead of notifying
on set, we notify on get. That's so we can lazy load objects.</p>

<p>As such, the getter events fire BEFORE the value is returned.
(You couldn't call anything after you returned
a value anyway)</p>
"""
@narr.testcase
def test_Injectable(self):
    subject = StrongBox()
    injector = object()
    subject.addInjector(injector)
    assert injector in subject.private.injectors
    subject.removeInjector(injector)
    assert injector not in subject.private.injectors
   

    # First the setter. Setters are easy. This is very useful for
    # transparent persistence (a la ZODB) and also for general
    # Model/View/Controller and Observer pattern stuff.
    # 
    # As such, the events are fired AFTER the value is set
    # in the object. (Contrast to getter events, below...)

@narr.testcase
def test_get_event(self):
    class Injector:
        def __init__(self):
            self.called = 0
        def getter_called(self, subject, name):
            self.called += 1
            self.name = name
            subject.name = "wilma"
    class Subject(StrongBox):
        name = attr(str)
    inj = Injector()
    sub = Subject(name="wanda")
    sub.addInjector(inj.getter_called)
    value = sub.name
    assert inj.called==1, \
           "should have been called 1 time (vs %i)" % inj.called
    assert inj.name == "name"
    assert value == "wilma", value


"""
The most usful reason for this is so that you can lazy-load
links and linksets. For example:
"""
@narr.testcase
def test_inject_linkset(self):
    class Parent(Strongbox):
        kids = linkset((lambda : Child), "parent")
    class Child(Strongbox):
        name = attr(str)
        parent = link(lambda : Parent)

    def makeKids(parent_obj, slot):
        if slot == 'kids':
            for x in range(10):
                parent_obj.private.kids << Child(name='kid number %s' % x)

    p = Parent()
    p.addInjector(makeKids)
    self.assertEquals(10, len(p.kids))




# *** private.isDirty
"""
<p>There's a bit of metadata called <code>.isDirty</code> that
says whether or not an object has been changed. This is to make
it easy to see what's changed when saving data. It's used by
<code>clerks</code>.</p>
"""
@narr.testcase
def test_isDirty(self):
    """
    this is for arlo...
    """
    class Dirt(StrongBox):
        x = attr(str)
    d = Dirt()
    # we start out dirty so that we get saved
    # (even if we're blank!)
    assert d.private.isDirty
    d = Dirt(x="dog")
    assert d.private.isDirty

    # but if something marks us clean, and then
    # we change, we should be dirty again!
    d.private.isDirty = 0
    d.x = "cat"
    assert d.private.isDirty


# * unit tests
"""
<p>This is the trick that makes the unit tests run:</p>
"""
if __name__=="__main__":
    unittest.main()
