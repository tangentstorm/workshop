
:mod:`strongbox` -- smart data objects with runtime type checking
=================================================================
.. module:: strongbox
   :synopsis: smart data objects with runtime type checking


class diagram
-------------

@TODO: redraw this! (basic idea is right, but some of the connectors are wrong)

.. image:: ../images/strongbox-classes.gif
   :alt: strongbox class diagram


overview
--------

Strongbox is a python module that lets you define data objects that
are rigorous about what attributes they have, and what values these
attributes let in.

Each attribute holds one type of value. Types are very flexible. They can be:
   * simple scalar types (str, int, float)
   * custom scalar types (FixedPoint, EmailAddress, etc)
   * anonymous types specified with regular expressions or lambdas
   * another strongbox class (via link attributes)
   * a list of a strongbox instances (via linkset attributes)
   * any other type (dict, list, class, function...) -- but these are kinda bad form

The attributes you defined are implemented using python 2.x's
properties and __slots__ features, so they are the only attributes
allowed on your object. But if you need to store arbitrary data
internally, that's fine - all instances have a member called
"private", which is just a plain old python object that you can do
whatever you like with.

You don't usually need to create getter and setter methods, but you
can if you want. Any method named get_XXX or set_XXX automatically
behaves as an accessor for the XXX attribute. You can even define
"virtual" attributes this way.

One of the main goals for strongbox is to provide classes that can be
easily mapped to and from a relational database. However, Strongboxes
are storage-agnostic and do not require any database to
work. Strongboxes implement the observer pattern, so they can notify
observers when they change; and also a variant called the "injector"
pattern, so they can trigger external lazy-loading schemes (such as
clerks.LinkInjector) whenever external data is needed.


usage
-----

When you define a strongbox class, you define a set of Attributes:

    >>> from strongbox import *
    >>> class Person(Strongbox):
    ...     name = attr(str)
    ...     age = attr(int, default=20, okay=lambda n: 0 < n < 150)
    ...     def get_canDrink(self):
    ...         return self.age >= 21
    
Attributes can be passed in on the constructor:

    >>> fred = Person(name="fred")
    >>> fred.name
    'fred'

Attributes can have validation rules and default values:

    >>> fred.age # note the default, above
    20
    >>> fred.canDrink
    0
    >>> fred.age = 50
    >>> fred.canDrink
    1
    >>> fred.age = 500
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
      File "/home/sabren/lib/strongbox/BoxMaker.py", line 81, in setter
        val = getattr(klass, slot).sanitize(val)
      File "/home/sabren/lib/strongbox/Attribute.py", line 83, in sanitize
        raise ValueError, repr(value) + " vs " + repr(self.okay)
    ValueError: 500 vs <function <lambda> at 0x81afacc>
    >>>



similar projects
----------------
Guido's explains metaclasses here:

  http://www.python.org/2.2/descrintro.html#metaclasses

SqlObject is similar to strongbox + arlo, but (as far as I can tell)
is tightly coupled to a database:

  http://sqlobject.org/

BasicProperty (and BasicTypes) for Python looks very similar, both in
spirit and implementation. This appears to be a fairly new project,
and I have not really looked into it:

  http://basicproperty.sourceforge.net/

WebWare's MiddleKit is also related:

  http://webware.sourceforge.net/Webware/MiddleKit/Docs/

