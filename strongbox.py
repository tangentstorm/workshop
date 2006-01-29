"""
strongbox: observable objects with runtime type checking.
"""
import sre
import types
import unittest
import warnings
from pytypes import Date
from types import StringType, LambdaType, ListType, NoneType

# * concept
"""
0208.2002 Strongbox Concept

Strongbox provides strongly-typed data objects for python.
These objects can be stored transparently in a relational
or object database.

* Strongbox is a metaclass.
Strongbox by itself doesn't do much. You subclass it,
and then your subclasses have the following properties:

** strong typing
Strongboxes are strongly typed. They have a set number of slots,
and each slot is associated with exactly one type of data.

These types may or may not correspond with python types. (They
could also be strings that match a regular expression, for 
example, or be defined with a function)

** magic getters and setters
get_xxx and set_xxx are magically understood to be accessors 
for the property xxx. There is no del_xxx because that
would violate strong typing. :)

All properties have getters and setters, even if you 
don't define them.

** observable
getters, setters, relationship operations, and method calls 
can all trigger events transparently.


* Persistence

** Clerk
One type of Observer is called Clerk. Clerk connects
to a Source and can give you a Strongbox, monitor
that strongbox for changes, and commit it back to the
source, either implicitly or explicitly.

** Sources
Sources provide low-level routines for loading and
storing strongbox objects. Generally, these are simple
adapters for existing storage solutions. 

The only Source bundled with the first version of strongbox
will be DBAPI2Source for relational databases.

** Schemas
Since relational databases store everything in tables,
we need a way of mapping objects to tables. This is done
with a simple Schema object.





* future
** lazy loading
If we have a tree or network of Nodes, we don't want
to have to load them all. Often - especially on the web -
we only care about one Node at a time, but we may also need
to get to some subset of their children.

Actually, I'm not sure lazy loading is the best solution 
for this. It might be simpler and faster to just load all
the nodes at once with one query.

** magic contracts
before_method(), after_method(), and always()
"""
# * old notes
"""
* strongbox module overview 
Strongbox is a tool for strongly-typed data objects in python.

* persistence
Persistence is not actually handled by strongbox. It will be handled
by an outside module, which defines the process of mapping strongboxes
to tables in a relational database (or to some other form of
persistence storage).

I'm worried about working with relationships though.

Imagine a simple Team/Player/Sport model:

   Team has players
   Players may be on several teams
   Each team has one sport

Here are the relationships:

   player.teams / team.players (junction)
   sport.teams (simple list)
   team.sport (simple reference)

The question is, if we remove the persistence ability from Strongbox,
how do we get the related objects?

For example:

>>> aTeam = clerk.load(Team, ID=123)
>>> aTeam.sport
???

What is sport? It's a Sport object, of course. But we can't just load
dependent objects all at once, because they could be connected in a
huge graph. (Eg, we load player 1, who's on several teams with
multiple players each, and those players are on multiple teams, and so
on....)  If we loaded dependent objects as soon as we loaded the main
object, we'd wind up with the whole database in memory. That might be
okay for a small database or an app server that stayed up for weeks,
but it's no good at all in a CGI script.

Instead, we want to load the main object, and only load dependent
objects if we need them.

So in the example above, we don't want aTeam.sport to actually be a
sport, but some object representing a reference to a Sport in the same
datastore that came from.

class ref(strongbox):
   _class = attr(type)
   _id = attr(long)
   _clerk = attr(object)

so maybe something like this:

class Sport(strongbox):
   pass
class Team(strongbox):
   sport = link(Sport)
class Player(strongbox):
   teams = join(Team)

Sport.teams = join(Team)
Team.players = join(Player)

* replacing zdc
@
how do I go from zdc to strongbox?

- replace dbc with clerk.load() or clerk.new() (except cursors)
- double check by adding a required parameter that only clerk passes
- remove parameter when done testing...

- replace xxx.save() with clerk.save()

- look for dbc.cursor lines and replace with storing to a map


eventually: force load to have a where clause!

save() should be dbc.save(obj), which doesn't exist yet,
but which is probably similar to Recordobject.save....
In any case, we can just make dbc.save call obj.save for
now.

Those are pretty much the only changes we need to make.
It's a lot of them, but it shouldn't be too hard. (Actually,
it'll probably mostly be test cases)

This should also localize the need for robj(ds), as it will
always be passed in from dbc.load()

We can also move all the _tablename nonsense, but I guess that can
wait a minute or two, until we start pulling in attributes.

Okay, well... Let's try it.

"""
# * forward
class forward:
    """
    dummy class for defining recursive structures)
    does absolutely nothing.
    """
    def __init__(self, typename=None):
        #@TODO: now that initialvalue passes instance,
        #@TODO: make forward('Whatever') take a module.Class
        #@TODO: and do some kind of morphing trick.
        if type(typename) != str:
            warnings.warn("forward() should be forward('module.ClassName')")
            
# * Notgiven
class Notgiven:
    "I'm a placeholder type distinct from None"
    
# * attr
# ** no tests yet :(
# ** code
class attr(property):
    """
    A small class representing a static attribute.
    """
    def __init__(self, typ, okay=None, default=Notgiven, allowNone=1):
        self.type = typ
        self.allowNone = allowNone
        self._determineDefault(typ, default)
        self._setOkay(okay)

    def __repr__(self):
        return "#< %s = %s(%s, ...) >#" % (
            self.__name__,
            self.__class__.__name__,
            self.type.__name__,
        )
        
    def _setOkay(self, okay):
        if type(okay) == str:
            self.okay = sre.compile(okay)
        elif type(okay) in (LambdaType, ListType, NoneType):
            self.okay = okay
        else:
            raise TypeError, "okay must be lambda, list, or string"

    def initialValue(self, instance=None):
        """
        instance should be ignored, except for links
        #@TODO: make links a separate interface
        """
        return self.cast(self.default)

    def _determineDefault(self, typ, default):
        self.default = default
        if default is Notgiven:
            if typ == str:
                self.default = ''
            elif typ in (int, float, long):
                self.default = 0
            else:
                self.default = None
            
    def cast(self, value):
        if value is None:
            return None # str(None) returns 'None', so we need a special case.
        elif isinstance(value, self.type):
            return value
        try:
            return self.type(value)
        except Exception, e:
            if value=="":
                #@TODO: see if this is really needed.
                #If so, explain. :)
                return None
            raise TypeError(self.__name__,value,self.type,str(e))

    def validate(self, value):
        if (value is None):
            return self.allowNone
        if self.okay is None:
            return 1
        elif type(self.okay)==LambdaType:
            return self.okay(value)
        elif type(self.okay)==ListType:
            return value in self.okay
        else:
            return self.okay.match(value) is not None
    
    def sanitize(self, value):
        if (self._typeok(value)) or (value is None):
            val = value
        else:
            val = self.cast(value)
        if not self.validate(val):
            raise ValueError(self.__name__, repr(value))
        return val # so the instance can store it


    def _typeok(self, value):
        """
        Factored out so I can override this in Link, etc.
        """
        return isinstance(value, self.type)
# * link
# ** test

class LinkTest(unittest.TestCase):

    def test_simple(self):
        class Child(Strongbox):
            name = attr(str)
        class Parent(Strongbox):
            kid = link(Child)
        p = Parent()
        p.kid = Child(name="damien")
        

    def test_typing(self):
        class LinkedListMember(Strongbox):
            next = link(forward)
        LinkedListMember.next.type=LinkedListMember

        class NonMember(Strongbox):
            pass

        class NotEvenAStrongbox:
            pass
        
        one = LinkedListMember()
        two = LinkedListMember()
        bad = NonMember()

        one.next = two
        two.next = one
        assert one.next.next is one

        failed = 0
        for item in (bad, NotEvenAStrongbox(), "wrong type"):
            try:
                one.next = item
            except TypeError:
                failed += 1
        assert failed == 3, "Link should force types"

        two = LinkedListMember()
        one = LinkedListMember(next=two)
        assert one.next is two
        assert two.next is None
# ** code
class link(attr):
    """
    Represents a one-way link to another Strongbox.
    """
    def __init__(self, klass):
        self.type = klass
        self.default = None
        self.okay = None
        self.allowNone = 1

    def _typeok(self, value):
        return isinstance(value, self.type)
    
# * TypedList
# ** no tests yet :(
# ** code
class TypedList(list):
    
    def __init__(self, klass, owner, backlink):
        super(TypedList, self)
        self.setType(klass)
        self.backlink = backlink
        self.owner = owner

    def setType(self, type):
        self.type = type

    def append(self, other):
        if type(other) == self.type:
            super(TypedList, self).append(other)
        else:
            raise TypeError, "Can't append %s to TypedList(%s)" \
                  % (type(other), self.type)
        if self.backlink is not None:
            setattr(other, self.backlink, self.owner)
    
    def __lshift__(self, other):
        self.append(other)
        return other
# * linkset
# ** test


class LinkSetTest(unittest.TestCase):

    def test_simple(self):

        class Child(Strongbox):
            mama = link(forward)
            name = attr(str)
        class Parent(Strongbox):
            kids = linkset(Child, "mama")
        Child.mama.type=Parent

        p = Parent()
        c = Child(name="freddie jr")
        p.kids << c
        assert p.kids[0] is c
        assert c.mama is p

    def test_typing(self):

        
        class Node(Strongbox):
            kids = linkset(forward, None)


        class NonNode:
            pass

        # should not be able to instantiate until we change the "forward" 
        self.assertRaises(ReferenceError, Node)
        Node.kids.type = Node
        
        # now it should work:
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
        
# ** code
class linkset(attr):

    def __init__(self, type, back):
        """
        type: the type of objects in the collection
        back: the name of the backlink in the child (can be None)

        For example, parent.children might have a backlink of
        child.parent so you'd say:

        class Parent(Strongbox):
            children = linkset(Child, 'parent')
        
        """
        self.type = type
        self.back = back      

    def initialValue(self, instance):
        if self.type == forward:
            raise ReferenceError, \
                  "Can't instantiate -- broken linkset(forward) promise."
        else:
            return TypedList(self.type, instance, self.back)

    def sanitize(self, other):
        raise AttributeError, "can't assign to linksets (only append/delete)"
# * Private
class Private(object):
    """
    This is just a plain old object. We create
    an instance on each StrongBox for storing
    private data. 
    """
    def __init__(self):
        pass
# * BoxMaker: the brains behind MetaBox
# ** no test yet :(
# ** code
class BoxMaker(object):
    """
    This is where the real work of MetaBox is done.
    It's just a normal object that builds a class.
    
    I separated it out because I wanted to hold
    some state information through the various
    phases of building the class:

    There are three passes:

       1. MetaBox.__new__ calls BoxMaker.start()
          which returns a new class
          
       2. MetaBox.__init__ calls BoxMaker.finish()
          which adds some magic property accesors

       3. StrongBox.__init__() then does some
          perfectly normal intitialization stuff
       
    """
    def __init__(self, type, name, bases, dict):
        self.type = type
        self.name = name
        self.bases = bases
        self.dict = dict
        self.attrs = [a for a in dict if isinstance(dict[a], attr)]
        self.slots = ["private"]

        self.addSlots()
        self.addAttrs()

    ## first pass (__new__): ################################

    def start(self):
        klass = type.__new__(self.type, self.name, self.bases, self.dict)
        klass.maker = self
        return klass

    def addSlots(self):
        for a in self.attrs:
            self.slots.append(a)
        self.dict["__slots__"] = self.slots

    def addAttrs(self):
        """
        this is really just for backwards compatability
        """
        attrs = {}
        for b in self.bases:
            if hasattr(b, "__attrs__"):
                attrs.update(b.__attrs__)
        for a in self.attrs:
            attrs[a] = self.dict[a]
            attrs[a].__name__ = a
        self.dict["__attrs__"] = attrs

    ## second pass (__init__) ###############################

    def finish(self, klass):
        self.addAccessors(klass)
        self.addAttrOwners(klass)

    def addAttrOwners(self, klass):
        for a in self.attrs:
            getattr(klass, a).__owner__ = klass

    def makeGetter(self, klass, slot):
        def getter(instance):
            instance.onGet(slot)
            return getattr(instance.private, slot)
        return getter

    def makeSetter(self, klass, slot):
        def setter(instance, val):
            val = getattr(klass, slot).sanitize(val)
            setattr(instance.private, slot, val)
            instance.onSet(slot, val)
        return setter
        
    def addAccessors(self, klass):
        props = {}
        
        # first get all the attributes:
        for a in self.attrs:
            props[a] = self.dict[a]

        # next, the getters and setters:
        getter = {}
        setter = {}
        for item in self.dict:
            slot = item[4:]
            if item.startswith("get_"):
                getter[slot] = self.dict[item]
                if slot not in self.attrs:
                    self.slots.append(slot)
            elif item.startswith("set_"):
                setter[slot] = self.dict[item]
                if slot not in self.attrs:
                    self.slots.append(slot)
            else:
                continue
            props.setdefault(slot, property())

        # now make the accessors:
        for slot in props:
            prop = props[slot]
            
            fget = getter.get(slot)
            if (slot in self.attrs) and (not fget):
                fget = self.makeGetter(klass, slot)
                
            fset = setter.get(slot)
            if (slot in self.attrs) and (not fset):
                fset = self.makeSetter(klass, slot)

            # this is the only way you can set .fget and .fset:
            property.__init__(prop, fget, fset)
            setattr(klass, slot, prop)
# * MetaBox
# ** test

class MetaBoxTest(unittest.TestCase):
    def test_simple(self):

        Person = MetaBox("Person", (), {
            "name" : attr(str, okay=['fred','wanda'], default="fred"),
        })

        assert type(Person) == MetaBox
        assert isinstance(Person.name, attr)
        assert Person.name.okay == ['fred','wanda']
        assert Person.name.__name__ == "name"
        assert Person.name.__owner__ == Person

        """
        That's really about all we can test here.
        
        The metaclass produces a class, but the
        class isn't very useful at that point.
        It's expecting to have methods like
        onSet, and onGet, and a .private ...
        but those things don't exist at this
        point in the object's lifecycle.
        
        That's why you subclass BlackBox
        or StrongBox instead of using MetaBox
        directly.
        """
# ** code
class MetaBox(type):
    """
    This is a metaclass. It's used to build a
    new strongbox subclass, which can then be
    instantiated.

    For an overview of metaclasses, see:
    
        http://www.python.org/2.2/descrintro.html

    You should not use this class directly.
    Rather, subclass StrongBox.

    The real work of this metaclass is in BoxMaker.
    """
    def __new__(meta, name, bases, dict):
        """
        This is where we create the new class. 

        meta: always a reference to MetaBox (this class)
        name: the name of the class being defined
        bases: tuple of base classes
        dict: namespace with the 'class' contents (defs, attributes, etc)
        """
        return BoxMaker(meta, name, bases, dict).start()
    
    def __init__(klass, name, bases, dict):
        """
        now that we have the class, we can do stuff to it.
        in this case, we'll add accessor methods.

        same args as above, except now we get the
        class instead of the metaclass
        """
        super(MetaBox, klass).__init__(name, bases, dict)
        klass.maker.finish(klass)
# * BlackBox
# ** test

    ## Private variables are explicitly private

    # All strongbox instances have a "private" namespace, which
    # lets them store private variables explicitly.

    def test_private(self):
        s = BlackBox()
        assert hasattr(s, "private")
        s.private.c = 1
        assert s.private.c == 1
        assert getattr(s, "c", None) is None


    ## Attributes have defaults, but can be initialized via the constructor
    
    def test_defaults(self):
        class Foo(BlackBox):
            bar = attr(int, default=5)  
        foo = Foo()
        assert foo.bar ==5
    
    def test_constructor(self):
        class Foo(BlackBox):
            bar = attr(int, default=5)  
        foo = Foo(bar=12)
        assert foo.bar == 12


    ## Without explicit defaults, strings default to '', ints and longs to 0

    def test_default_defaults(self):
        class Foo(BlackBox):
            m_str = attr(str)
            m_int = attr(int)
            m_long = attr(float)
            m_float = attr(float)
            n_int = attr(int, default=None)
            n_str = attr(str, default=None)
        foo = Foo()
        assert foo.m_str == ''
        assert foo.m_int == 0
        assert foo.m_long == 0
        assert foo.m_float == 0
        assert foo.n_int is None
        assert foo.n_str is None

    ## Other types pass defaults to the constructor
    
    def test_othertypes(self):
        class UpCase:
            def __init__(self, value): self.value = str(value).upper()
            def __cmp__(self, other): return cmp(self.value, other)
            def __repr__(self): return value
        class Foo(BlackBox):
            bar = attr(UpCase, default="xyz")
            abc = attr(str, default="xyz")
        foo = Foo()
        assert foo.bar == "XYZ", foo.bar
        assert foo.abc == "xyz", foo.abc


    ## Attributes use (runtime) static typing
    
    def test_static_typing(self):
        class Foo(BlackBox):
           bar = attr(int)
        foo = Foo()
        try:
           goterr = 0
           foo.bar = "not an int value"
        except TypeError:
           goterr = 1
        assert goterr, "should get TypeError assigning string to int attr"
    
    
    def test_okay_lambda(self):
        class Foo(BlackBox):
            bar = attr(int, lambda x: 5 < x < 10)
        foo = Foo()
        foo.bar = 7 # should work
        try:
           goterr = 0
           foo.bar = 10
        except ValueError:
            goterr = 1
        assert goterr, "the lambda should have rejected bar=10"
    
    
    def test_okay_list(self):
        class Paint(BlackBox):
            color = attr(str, ["red", "green", "blue"])
        p = Paint()
        p.color = "red" # should work
        try:
            goterr = 0
            p.color = "orange"
        except ValueError:
            goterr = 1
        assert goterr, "values not in the list should be rejected"
    
        
    def test_okay_regexp(self):
        class UsCitizen(BlackBox):
            ssn = attr(str, r"\d{3}-?\d{2}-?\d{4}")
        
        elmer = UsCitizen()
        elmer.ssn = "404-44-4040" # should work
        try:
            goterr = 0
            elmer.ssn = "867-5309"
        except ValueError:
            goterr = 1
        assert goterr, \
               "ssn regexp should reject phone numbers - even famous ones"


    ## dealing with None / empty strings ########################
    
    def test_allowNone(self):
        """
        Attributes allow "None" by default
        """
        class Foo(BlackBox):
           bar = attr(int)
        foo = Foo()
        try:
           goterr = 0
           foo.bar = None
        except ValueError:
           goterr = 1
        assert not goterr, "assigning None didn't work!"    
   
    def test_dontAllowNone(self):
        """
        We can disallow None if we want.
        """
        class Foo(BlackBox):
           bar = attr(int,allowNone=0)
        foo = Foo(bar=15)
        try:
           goterr = 0
           foo.bar = None
        except ValueError:
           goterr = 1
        assert goterr, "assigning None should have failed!"

    def test_emptyString(self):
        """
        Should convert empty strings to None, unless
        it actually IS a string. This is so we can
        pass None in from an HTML form.

        Really, I don't think the browser should send an
        empty string, but IE5.00.2614.3500 sure seems to,
        so let's deal with it. :)
        """
        class Foo(BlackBox):
            i = attr(int)
            s = attr(str)
            d = attr(Date)
        f = Foo()
        f.i = ""; assert f.i is None
        f.s = ""; assert f.s is ""
        f.d = ""; assert f.d is None

        

    def test_inheritance(self):
        class Dad(BlackBox):
            nose = attr(str, default="big")
        class Son(Dad):
            pass
        assert Son().nose == "big"
# ** code
"""
I thought about factoring out a
BaseBox... But I just couldn't
think of a difference, and I like
the name BlackBox better. 
"""
class BlackBox(object):
    __metaclass__ = MetaBox
    
    def __init__(self, **kwargs):
        self.__private__()
        for slot, attr in self.__attrs__.items():
            setattr(self.private, slot, attr.initialValue(self))
        self.update(**kwargs)

    def __private__(self):
        self.private = Private()        

    def update(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def onSet(self, slot, value):
        pass

    def onGet(self, slot):
        pass

    def __repr__(self):
        # for linksets and in other cases where objects refer
        # back to each other, this could create an infinite loop,
        # so we only show plain attributes.
        return "%s(%s)" % (self.__class__.__name__ ,
                           ", ".join(["%s=%s" % (a, getattr(self, a))
                                      for a,v in self.__attrs__.items()
                                      if v.__class__ is Attribute]))
    

##    ## this stuff is for pickling... but it turns out pickling
##    ## is a can of worms when you have injectors lying around.
##    ## I think maybe you can use pickle OR clerk but not both.
##    ## I haven't tested that theory though.
##   
##     def memento(self):
##         res = {}
##         for a in self.__attrs__:
##             res[a]=getattr(self,a)
##         return res
##     def __getstate__(self):
##         return self.memento()
##     def __setstate__(self, memento):
##         self.__private__()
##         self.update(**memento)
    pass
# * WhiteBox
# ** test
class WhiteBoxTest(unittest.TestCase):

    # we implement the famous Gang of Four Observer pattern:
    
    def test_Observable(self):
        subject = WhiteBox()
        observer = object()
        subject.addObserver(observer)
        assert observer in subject.private.observers
        subject.removeObserver(observer)
        assert observer not in subject.private.observers

    # Injectable is like Observable, but instead of notifying
    # on set, we notify on get. That's so we can lazy load objects:

    def test_Injectable(self):
        subject = WhiteBox()
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

    def test_set_event(self):
        class Observer:
            def __init__(self):
                self.updated = False
            def update(self, subject, name, value):
                self.updated = True
                self.name = name
                self.value = value
        class Subject(WhiteBox):
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
    

    # Getters, on the other hand are useful for lazy loading.
    # As such, the events get fired BEFORE the value is returned.
    # 
    # Of course, you couldn't call anything after you returned
    # a value anyway :)

    def test_get_event(self):
        class Injector:
            def __init__(self):
                self.called = 0
            def getter_called(self, subject, name):
                self.called += 1
                self.name = name
                subject.name = "wilma"
        class Subject(WhiteBox):
            name = attr(str)
        inj = Injector()
        sub = Subject(name="wanda")
        sub.addInjector(inj.getter_called)
        value = sub.name
        assert inj.called==1, \
               "should have been called 1 time (vs %i)" % inj.called
        assert inj.name == "name"
        assert value == "wilma", value

    def test_isDirty(self):
        """
        this is for arlo...
        """
        class Dirt(WhiteBox):
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
# ** code
class WhiteBox(BlackBox):
    """
    Base class for observable, injectable data
    objects with runtime type checking.
    """
    def __private__(self):
        self.private = Private()
        self.private.isDirty = True # so new objects get saved
        self.private.observers = []
        self.private.injectors = []

    ## for notifying other classes of changes:
    def addObserver(self, callback):
        self.private.observers.append(callback)
    def removeObserver(self, callback):
        self.private.observers.remove(callback)
    def notifyObservers(self, slot, value):
        for callback in self.private.observers:
            callback(self, slot, value)

    def onSet(self, slot, value):
        self.notifyObservers(slot, value)
        self.private.isDirty = True

    ## for lazy loading, etc:
    def addInjector(self, callback):
        self.private.injectors.append(callback)
    def removeInjector(self, callback):
        self.private.injectors.remove(callback)
    def notifyInjectors(self, slot):
        for callback in self.private.injectors:
            callback(self, slot)

    def onGet(self, slot):
        self.notifyInjectors(slot)
        
# * BoxView
# ** no tests yet :(
# ** code
"""
note: this was moved here from zdc. It's useful for
zebra templates, but it's not really integrated
with strongbox yet.
"""
class BoxView:
    """
    Builds a view (dict/list data structure) from a Box
    """
    __ver__="$Id: BoxView.py,v 1.4 2006/01/20 18:22:45 sabren Exp $"

    def __init__(self,object):
        self.object = object

    def __getitem__(self, name):
        # this used to have a try..except block, but it made it
        # very hard to debug!
        try:
            res = getattr(self.object, name)
        except AttributeError:
            raise AttributeError("couldn't read attribute '%s'" % name)
        try:
            hasLen = 1
            len(res)
        except:
            hasLen = 0
        if (hasLen) and (type(res) != str):
            lst = []
            for item in res:
                lst.append(BoxView(item))
            return lst
        else:
            return res

    def __getattr__(self, name):
        if name=="object":
            return getattr(super(BoxView, self), name)
        else:
            return getattr(self.object, name)

    def get(self, name, default=None):
        return getattr(self.object, name, default)

    def keys(self):
        return self.object.__slots__
        #@TODO: ObjectView.keys() only works with RecordObjects
        #map(lambda fld: fld.name, self.object._table.fields) \
        #return self.object.__values__.keys() \
        #       + self.object._links.keys()
               # NOTE: i was only doing the tuple thing
               #       because of zikeshop.Product

# * Strongbox = WhiteBox
Strongbox = WhiteBox
# * --
if __name__=="__main__":
    unittest.main()
    
