#!/usr/bin/env python2.5
from narrative import testcase, addMethod
from strongbox import *
from unittest import TestCase
from clerks import *
from storage import RamStorage
import unittest

# * Clerk: Executive Overview
"""
Use the clerks module if:

  - you want to load, save, and query data objects
    in some kind of persistent storage system such
    as a relational database.

  - You want to load and save large graphs of
    interconnected objects efficiently, (lazy
    loading and caching)

  - You want to add arbitrary behavior when you
    save objects.


You use clerks, you need:

  - you use strongbox to define your data classes
  
  - you follow the convention of giving all objects a numeric ID
  
  - you use one of the storage backends provided by the storage
    module (including RamStorage if you just want an in-memory database)


Clerks allo you write efficient code in both short-lived
CGI-like environments (thanks to lazy loading), as well
as long-running server processes (where caching and
indexing allow fast in-memory operations).

Because clerks rely heavily on caching, they are NOT designed
to be used in long-running servers where other programs are
making frequent changes to the underlying database. (It's okay
for any number of clients to read the database, of course).
Rather, all clients should write data by dealing directly
with the Clerk.
"""

# * about this document
"""
This document serves as exectuable specification for clerks.
It contains a detailed explanation of the module as well
as numerous code sections that serve both as unit tests
and examples for users.
"""


# * objects used in the examples

class Record(Strongbox):
    ID = attr(int)
    value = attr(str)
    next = link(lambda : Record)

class Node(Strongbox):
    ID = attr(int)
    data = attr(str)
    parent = link(lambda : Node)
    kids = linkset((lambda : Node), "parent")



"""
We'll store each Record in a table called 'records_table'
and we'll use a column called 'nextID' to hold the ID
of the 'next' link.
"""

RECORD_TABLE = "record_table"
NODE_TABLE = "node_table"



"""
To make this work, we need to define a schema.
The schema is just a wrapper around a dictionary,
which maps classes to table names and link attributes
to foreign key column names.

Here is the schema for our Record object:
"""

TEST_SCHEMA = Schema({
    Node: NODE_TABLE,
    Node.parent: "parentID",
    Record: RECORD_TABLE,
    Record.next: "nextID",
})


"""
Here is are top level test structure. Many of our
test classes share a common setup, so it makes sense
to group them into a single TestCase class.

Since these are just tests, we'll be using a RamStorage
object, which is a simple collection of tables that stay
in memory. The exact same concepts apply to any storage
backend, however - including MySQL, SQLite, or any other
service implementing the storage interface.
"""

class ClerkTest(unittest.TestCase):
    def setUp(self):
        self.storage = RamStorage()
        self.clerk = Clerk(self.storage, TEST_SCHEMA)



# * basic usagenterface: .store and .fetch
"""
You need these things to use clerk:

  - a strongbox data class (see strongbox.py)
  - an attribute called ID on the strongbox
  - a storage object (see storage.py)
  - a clerks.Schema object (see below)


Here's how to store and retrieve a record:
"""

@addMethod(ClerkTest)
def test_basics(self):

    # create and store a record
    r = Record(value='hello')

    # notice the ID is blank:
    assert r.ID == 0 
    assert r.next is None

    # now store it:
    self.clerk.store(r)

    # note that the object is updated in place:
    assert r.ID == 1
    assert r.next is None

    # here's what's in the table:
    # note the nextID is 0 because r.next is None
    db_row = self.storage.match(RECORD_TABLE)
    assert db_row == [{"ID":1, "value":"hello", "nextID":0}], db_row

    # now we can retrieve it by passing the ID to fetch
    a = self.clerk.fetch(Record, 1)

    # we can also pass in a where clause if we KNOW we'll only
    # get one record back. (To match more than one record, use
    # match. - see below.)
    b = self.clerk.fetch(Record, value='hello')

    # and note that we always get the same object,
    # so if you change one, they all change.
    c = self.clerk.fetch(Record, 1)
    assert a is r
    assert b is r
    assert c is r


# * storing objects

@addMethod(ClerkTest)
def test_store(self):
    self.clerk.store(Record())
    actual = self.storage.match(RECORD_TABLE)
    assert actual == [{"ID":1, "value":"", "nextID":0}], actual
    r = self.clerk.fetch(Record, 1)
    assert r.next is None


@addMethod(ClerkTest)
def test_store_again(self):
    self.clerk.store(Record())
    r = self.clerk.fetch(Record, 1)
    r.value = "abc"
    self.clerk.store(r)
    assert len(self.storage.match(RECORD_TABLE))==1


"""
Note that if you store an object that's connected to
other objects through strongbox.link , it saves the
linked object first.

This makes sense, because in order to store a foreign
key reference in the database, we've got to store the
foreign object and get its auto-generated key value.
"""

@addMethod(ClerkTest)
def test_store_link(self):
    r = Record(value="a")
    r.next = Record(value="b")

    self.clerk.store(r)
    del r
    r = self.clerk.match(Record, value="a")[0]
    assert r.ID == 2, "didn't save links first!"
    assert r.next is not None, "didn't store the link"
    assert r.next.value=="b", "didn't store link correctly"

    r.next = None
    self.clerk.store(r)
    r = self.clerk.match(Record, value="a")[0]
    assert r.next is None, "didn't delete link!"

    r = Record(value="noNext")
    self.clerk.store(r)
    r = self.clerk.fetch(Record, value="noNext")
    assert r.next is None


"""
However, with linksets, we have the opposite situation.
The parent object has to be stored first so the child
objects can reference its primary key.
"""

@addMethod(ClerkTest)
def test_store_linksets(self):
    n1 = Node(data="a")
    n1.kids << Node(data="aa")
    n1.kids << Node(data="ab")
    n1.kids[1].kids << Node(data="aba")
    self.clerk.store(n1)
    assert len(n1.kids)== 2, [(k.ID, k.data) for k in n1.kids]        

    n = self.clerk.fetch(Node, 1)
    assert n is n1
    assert len(n1.kids)== 2, \
           "fetch corrupted kids: %s" % [(k.ID, k.data) for k in n1.kids]

    assert n.ID == 1, "didn't save parent of linkset first!"
    assert len(n.kids)== 2, \
           "didn't store the linkset: %s" % [(k.ID, k.data) for k in n.kids]
    assert n.kids[0].data=="aa", "didn't store link correctly"
    assert n.kids[1].data=="ab", "didn't store link correctly"
    assert n.kids[1].kids[0].data=="aba", "didn't store link correctly"
    assert n.kids[0].parent is n
    assert n.kids[1].parent is n

    n.kids[1].parent=None
    n.kids.remove(n.kids[1])
    self.clerk.store(n)
    n = self.clerk.match(Node, data="a")[0]
    assert len(n.kids) == 1


# * fetching objects

@addMethod(ClerkTest)
def test_fetch(self):
    self.clerk.store(Record(value="howdy"))

    # we can pass in an ID:
    obj = self.clerk.fetch(Record, 1)
    assert obj.value == "howdy"

    # or we can use keywords:
    # @TODO: this should probably be deprecated in favor of .matchOne
    obj = self.clerk.fetch(Record, value="howdy")
    assert obj.value == "howdy"


def test_fetch_from_wide_table(self):
    """
    Supose a strongbox has 1 slot, but the table has 2+ columns.
    We can't just jam those columns into the strongbox,
    because strongbox is *designed* to blow up if you try
    to add new attributes.

    But on the other hand, a DBA should be able to add columns
    to the databaes without breaking the code and causing
    AttributeErrors all over the place.

    Instead, Clerk should only use the columns that have
    matching attributes, and simply ignore the others.

    This sorta violates the concept of OnceAndOnlyOnce,
    because now the tables can be out of sync with the
    data model, but I think it's better than the alternative,
    and this is the sort of thing one could check with
    an automated tool.

    #@TODO: write tool to compare DB and object models :)
    """
    try:
        self.storage.store(RECORD_TABLE, value="a", extra_column="EEK!")
        a = self.clerk.fetch(Record, 1)
        a.value="aa"
        self.clerk.store(a)
    except AttributeError:
        self.fail("shouldn't die when columns outnumber attributes")


@addMethod(ClerkTest)
def test_fetch_with_calculated_columns(self):
    """
    Along those lines, if the table caches calculated
    fields we need to filter them out when we fetch
    """
    class Calculated(StrongBox):
        ID = attr(int)
        a = attr(int)
        def get_b(self):
            return 5
        c = attr(int)
    calc = self.clerk._rowToInstance({"ID":0, "a":1,"b":2,"c":3}, Calculated)
    assert calc.a == 1
    assert calc.b == 5
    assert calc.c == 3

    # the point is, b has to be ignored because
    # normally it raises an error:
    self.assertRaises(AttributeError, setattr, calc, "b", 2)



# * matching objects

@addMethod(ClerkTest)
def test_match(self):
    self.clerk.store(Record(value="one"))
    self.clerk.store(Record(value="two"))
    self.clerk.store(Record(value="two"))
    assert len(self.clerk.match(Record, value="zero")) == 0
    assert len(self.clerk.match(Record, value="one")) == 1
    assert len(self.clerk.match(Record, value="two")) == 2


# @TODO: ought to have a test case about where/arlo


@addMethod(ClerkTest)
def test_matchOne(self):
    self.clerk.store(Record(value="one"))
    self.clerk.store(Record(value="two"))
    self.clerk.store(Record(value="two"))

    try:
        self.clerk.matchOne(Record, value="zero")
        self.fail("should have failed for not matching")
    except LookupError: pass

    assert isinstance(self.clerk.matchOne(Record, value="one"),
                      Record)

    try:
        self.clerk.matchOne(Record, value="two")
        self.fail("should have failed for matching two")
    except LookupError: pass



# * deleting objects
"""
To delete an object, you simply pass the class and
key to clerk.delete()

Note that you are responsible for unlinking the
object from other objects in memory so that the
object does not get re-saved to the database.
"""

@addMethod(ClerkTest)
def test_delete(self):
    self.test_fetch()
    self.clerk.delete(Record, 1)
    assert self.storage.match(RECORD_TABLE) == []



# * Lazyloading with Stubs and Injectors

# ** what are stubs?
"""
Stubs are simply strongboxes that have not yet been filled in.

Every strongbox can at least potentially correspond to a row in
the database. Stubs are no exception, but they correspond to rows
that the clerk has not yet loaded.

For example, given a child table with a parentID field, and
a row where parentID=5 , we can infer the existence of a row
in the parent table having ID=5. 

When clerk encounters this situation, it will simply create a new
strongbox, Parent(ID=5).

Now you can assert that  child.parent.ID == 5

But what happens when you ask for child.parent.name ?
The name field is still stored in the database.

Remember, a strongbox is not tightly coupled to the storage
mechanism. This means it does not have access to the Clerk object,
so it cannot simply load the data.

Instead, strongboxes implement an interface called Injectable,
similar to the Observable interface from the Obsever Design Pattern
(which strongbox also implements).

Basically, strongbox allows you to register a callback that gets
fired off whenever a field like .name is accessed. The injector
can then insert (or modify) the data automatically *before* the
.name field is returned to the caller.

Clerks utilize two types of Injectors:

  LinkInjector populates in a single stub with live data.
  LinkSetInjector populates a linkset with live objects.

"""

# ** what are injectors?
"""
Imagine that you have a tree of objects 10 levels deep. For
example, a relationship mapping bosses to subordinates.
You don't want to have to load the whole tree just to retrieve
the CEO of a company.

If we'd gone the SQLObject route, then every object knows
about the database, so it's easy to for the object to just load
each level of the hierarchy directly. But our objects don't
know anything about how they're stored. So how to handle that?

What we do is we do is create a shell object. That is, an
object that holds the place of a record but not the data.

Imagine a tree that looks like this:

        office - manager - projects
                   |
        office - workers - projects


class Office:
    manager = link(lambda: Person)
    workers = linkset(lambda: Person)

class Person:
    office = link(Office)
    projects = linkset(lambda: Project)

class Project

# todo: this ought to be modelled with roles, so find
# a better example for this kind of thing.

That is, everyone in each office is assigned to
certain projects, and every office has some number
of workers and one manager. This is sort of a contrived
example, but it allows us to look at two situations:
the list of manager projects for an office and the
list of worker projects for an office.

If you imagine a database with this information, you can see
it's easy to get all the offices: select * from office.
In our scheme here, it looks like clerk.match(Office)

In the database, the Office table would have managerID
column, and there would be a separate table for
workers: ID, officeID, personID

...

I'm trying to show that we have empty objects, and you can't
tell what state they're in until they're observed.

PEAK seems to do this with bindings...
SQLObject seems to just hold on to the database connection.
clerk takes advantage of injectors.

Start with linkset. They're just like select all.

But what if it's a 1-1 relationship? some options:

  a load each one individually (explosion!)
  b do the join up front in sql
  c load and cache the whole table
  d don't load anything

Arlo takes option c or d. option b would be nice but isn't
implemented.  So I want to show that you can load a hollow manager
object and it will know its ID, and can therefore load its projects
without ever reading the manager data from the database!!

What about the tree explosion? Well, you can just read the
whole table at once up front...


"""
# ** LinkInjector


@addMethod(ClerkTest)
def test_link_injection(self):
    self.storage.store(RECORD_TABLE, value="a", nextID=2)
    self.storage.store(RECORD_TABLE, value="b", nextID=3)
    self.storage.store(RECORD_TABLE, value="c", nextID=None)

    a = self.clerk.fetch(Record, 1)

    self.assertEquals('a', a.value)
    assert a.next.private.isStub
    assert len(a.next.private.injectors) == 1
    self.assertEquals('b', a.next.value)
    self.assertEquals('c', a.next.next.value)
    assert a.next.next.next is None


"""
Here's a more involved example.
"""

@testcase
def test_link_inject(self):

    class Foreign(Strongbox):
        ID = attr(int)
        data = attr(str)

        # there's no explicit test for this,
        # but this is here to make sure that inject
        # handles stored calculated fields properly
        def get_calc(self):
            return 2+2

    class Local(Strongbox):
        ref = link(Foreign)

    schema = Schema({
        Foreign: "foregin",
        Local: "local",
        Local.ref: "foreignID",
    })
    clerk = RamClerk(schema)

    # first, we store an object...
    clerk.store(Foreign(data="Here I come to save the day!"))

    # now here's the local object with a stubbed out reference
    # to that object.
    
    # (note: you wouldn't normally do this by hand, since
    # clerk does it for you)
    
    obj = Local()
    assert obj.ref is None
    obj.ref = Foreign(ID=1)
    obj.ref.private.isStub = True # required!

    obj.ref.addInjector(LinkInjector(clerk, Foreign, 1).inject)
    assert len(obj.ref.private.injectors) == 1

    # should be able to fetch the ID without triggering load
    assert obj.ref.ID == 1
    assert obj.ref.private.data == ""
    assert len(obj.ref.private.injectors) == 1

    # but getting any other field triggers the load...
    self.assertEquals("Here I come to save the day!", obj.ref.data)
    assert len(obj.ref.private.injectors) == 0


# ** LinksetInjector

@addMethod(ClerkTest)
def test_linkset_injection(self):
    self.storage.store(NODE_TABLE, data="top", parentID=None)
    self.storage.store(NODE_TABLE, data="a",   parentID=1)
    self.storage.store(NODE_TABLE, data="a.a", parentID=2)
    self.storage.store(NODE_TABLE, data="b",   parentID=1)

    top = self.clerk.fetch(Node, 1)
    assert top.kids[0].data == "a"
    assert top.kids[1].data == "b"
    assert top.kids[1].kids == []
    assert top.kids[0].kids[0].data == "a.a"



@testcase
def test_linkset_inject(self):


    class Content(Strongbox):
        ID = attr(int)
        box = link(lambda : Package)
        data = attr(str)


    class Package(Strongbox):
        ID = attr(int)
        refs = linkset(Content, "box")


    ms = RamStorage()
    ms.store("Package")
    ms.store("Content", data="I'm content", boxID=1)
    ms.store("Content", data="I'm mal content", boxID=1)

    schema = Schema({
        Content: "content",
        Content.box: "boxID",
        Package: "package",
    })

    clerk = Clerk(ms, schema)

    pak = Package()
    pak.refs << Content(data="I'm content", box=pak)
    pak.refs << Content(data="I'm malcontent", box=pak)
    pak = clerk.store(pak)

    # @TODO: should be able to add to the index without
    # triggering load (for performance reasons)
    # -- so long as any other use DOES trigger load --


    clerk.cache.clear()
    pak = clerk.fetch(Package, ID=1)

    # asking for .refs will trigger the load:
    assert len(pak.private.refs) == 0, pak.private.refs
    assert len(pak.refs) == 2

    # make sure it works with << on a fresh load too:
    newClerk = Clerk(clerk.storage, clerk.schema)
    pak = newClerk.fetch(Package, ID=1)
    assert len(pak.private.refs) == 0
    pak.refs << Content(data="I'm malcontent",  box=pak)
    assert len(pak.refs) == 3


# ** using links and linksets together

@testcase
def test_linkinjector_with_linkset(self):
    """
    what happens if the thing we're injecting
    has a linkset of its own (this used to fail)
    """

    class Kid(Strongbox):
        ID = attr(int)
        parent = link(lambda : Parent)

    class Parent(Strongbox):
        ID = attr(int)
        name = attr(str)
        kids = linkset(Kid, "parent")

    class Uncle(Strongbox):
        brother = link(Parent)

    schema = Schema({
        Kid: "kid",
        Kid.parent: "parentID",
        Parent: "parent",
        Uncle: "uncle",
        Uncle.brother: "brotherID",
    })
    clerk = RamClerk(schema)


    kid = Kid()
    dad = Parent(name="Brother Dad")
    dad.kids << kid
    clerk.store(dad)

    # here, we're making a stub by hand again.
    # again, you normally don't do this by hand.
    unc = Uncle()
    unc.brother = Parent(ID=1)
    unc.brother.private.isStub = True
    unc.brother.addInjector(LinkInjector(clerk, Parent, 1).inject)

    ## this next line threw an AttributeError because the
    ## injector tried to include "kids" in the .update() call
    self.assertEquals("Brother Dad", unc.brother.name)


# * avoiding unnecessary writes: the private.isDirty flag
"""
Every Strongbox has a (semi) private .isDirty flag.
When this flag is set to False, the clerk will not
bother updating the storage.
"""
@addMethod(ClerkTest)
def test_dirt(self):
    # dirty by default (already tested in strongbox)
    r = Record()
    assert r.private.isDirty

    # but not after a store:
    r = self.clerk.store(r)
    assert not r.private.isDirty

    # and not after a fetch:
    r = self.clerk.fetch(Record, ID=1)
    assert not r.private.isDirty

    # or a match:
    r = self.clerk.match(Record)[0]
    assert not r.private.isDirty


@addMethod(ClerkTest)
def test_dirty_recursion(self):
    r = Record()
    r.next = Record()
    r.next.next = r
    assert r.private.isDirty
    assert r.next.private.isDirty
    r = self.clerk.store(r)
    assert r.ID == 2
    assert r.next.ID == 1

    r = self.clerk.fetch(Record, 2)
    assert not r.private.isDirty
    assert not r.next.private.isDirty


    ## and the same thing for linksets:
    n = Node()
    n.kids << Node()
    n.kids[0].kids << n
    assert n.private.isDirty
    assert n.kids[0].private.isDirty
    n = self.clerk.store(n)

# * stubs

@addMethod(ClerkTest)
def test_stub(self):
    self.clerk.store(Record(value="a", next=Record(value="b")))
    self.clerk.cache.clear()
    recA = self.clerk.fetch(Record, value="a")
    recB = self.clerk.fetch(Record, value="b")
    assert recA.next.ID == recB.ID
    assert recA.next is recB


# * caching objects
"""
The cache is there so we don't have to repeatedly request
data from the database.


The cache is currently implemented as a dictionary mapping
clases to dictionaries of instances. That is:

   cache.data[Class][instance.ID] = instance

The reason for this organization is so that we can cache
entire tables of objects at once, and can quickly scan through
those tables ourselves when we need to load a linkset.

Right now, cache queries are limited to simple equalities.
That is, you can match where a particular field equals a
particular value, but you can't query for fields 'greater than'
the value.

Ideally, *every* match would use these cached tables, but
that won't work unless we implement our own little query
language. (A start on this actually exists in storage with
the QueryBuilder but it doesn't currenly work with clerks.)

"""
# ** cache basics
"""
The basic test of the cache: if you store something and
fetch it back, you get the exact same instance in memory.
"""
@addMethod(ClerkTest)
def test_cached_fetch(self):
    self.clerk.store(Record(value="one"))
    rec1a = self.clerk.fetch(Record, 1)
    rec1b = self.clerk.fetch(Record, 1)
    assert rec1a is rec1b

    n = Record()
    r = Record(next=n)        
    assert self.clerk.store(r) is r
    assert self.clerk.cache[(Record, r.ID)] is r
    assert self.clerk.cache[(Record, n.ID)] is n
    assert self.clerk.cache[(Record, n.ID)] is r.next

@addMethod(ClerkTest)
def test_cached_match(self):
    rb = self.clerk.store(Record(value="b"))
    ra = self.clerk.store(Record(value="a", next=rb))

    a,b = self.clerk.match(Record, orderBy="value")
    assert a is ra
    assert b is rb

# ** caching entire tables

@addMethod(ClerkTest)
def test_cached_class(self):
    """
    This shows that if we run cacheAll(Record)
    then we wind up with 4 records in the cache.
    and the class is noted in the cache's allCached
    dictionary.
    """
    self.storage.store(RECORD_TABLE, value='a')
    self.storage.store(RECORD_TABLE, value='b')
    self.storage.store(RECORD_TABLE, value='c')
    self.storage.store(RECORD_TABLE, value='d')
    self.clerk.cacheAll(Record)
    assert Record in self.clerk.cache.allCached
    assert len(self.clerk.cache.data[Record].keys()) == 4
    
    """
    Now for the kicker:
    We wipe the underlying table...
    """
    for x in range(1,5): self.storage.delete(RECORD_TABLE, x)
    assert self.storage.match(RECORD_TABLE) == []

    """
    But we can still get the object:
    """
    a = self.clerk.matchOne(Record, value='a')
    assert a.ID == 1
    assert a.value == 'a'


# ** linkinjectors and the cache
"""
Here's our basic linkinjector test again, but this
time, we're going to rely on the cache.

When we call .cacheAll(Record) here, each row in the
database is converted into an object.

Since we happen to be using a RamStorage for these tests,
the RECORD_TABLE records will be matched in the order
they were defined -- that's just how RamStorage works.

So imagine what happens as we cache the table:

  - the first record, ID=1, value='a' , nextID=2 is encountered
  - the record with ID=2 has not been seen yet, so a stub is created:
      - rec2Stub = Record(ID=2) # + injectors
  - and cached:
      - cache[Record,2] <= rec2Stub
  - the stub is added to a live object for the first row:
      - rec1 =  Record(value='a', next=rec2Stub)
  - the live record is cached:
      - cache[Record,1] <= rec1
  
  - now we match the second row, with ID=2, value='a', nextID=3
  - cache[Record, 2] already exists, so we just use it:
      - rec2 = cache[Record,2]
  - we create a stub for rec3:
      - rec3stub = ...
  - since we have the live data, we can fill it in:
      - rec2.private.value='a'
      - rec2.private.next = rec3Stub

At this point we have 2 live objects and a stub.

But wait a second! What about the injectors we added to record
2 when it was a stub? They're still there! So now, when we ask
for rec1.next.value ... It hits up the storage system again! All
our caching effort was wasted.

So.. To keep that from happening, the linkinjector always checks
to make sure the object is still a stub before it does anything.

@TODO: when caching entire tables, mark them somehow so that
the LinkInjectors aren't added to stubs in the first place.

"""

@addMethod(ClerkTest)
def test_cached_link_injection(self):
    self.storage.store(RECORD_TABLE, value="a", nextID=2)
    self.storage.store(RECORD_TABLE, value="b", nextID=3)
    self.storage.store(RECORD_TABLE, value="c", nextID=None)

    # cache the objects and drop the underlying table
    self.clerk.cacheAll(Record)
    self.storage.delete(RECORD_TABLE, 1)
    self.storage.delete(RECORD_TABLE, 2)
    self.storage.delete(RECORD_TABLE, 3)

    a = self.clerk.fetch(Record, 1)

    self.assertEquals('a', a.value)

    # if a.next.value fires off an injector,
    # this next line will hit the empty table and crash!
    self.assertEquals('b', a.next.value)
    self.assertEquals('c', a.next.next.value)
    assert a.next.next.next is None




# ** linksetinjectors and the cache
"""
Here's the same deal for linksetinjectors
"""

@addMethod(ClerkTest)
def test_cached_linkset_injection(self):
    self.storage.store(NODE_TABLE, data="top", parentID=None)
    self.storage.store(NODE_TABLE, data="a",   parentID=1)
    self.storage.store(NODE_TABLE, data="a.a", parentID=2)
    self.storage.store(NODE_TABLE, data="b",   parentID=1)

    # cache and drop table
    self.clerk.cacheAll(Node)
    self.storage.delete(NODE_TABLE, 1)
    self.storage.delete(NODE_TABLE, 2)
    self.storage.delete(NODE_TABLE, 3)
    self.storage.delete(NODE_TABLE, 4)

    top = self.clerk.fetch(Node, 1)
    assert top.kids[0].data == "a"
    assert top.kids[1].data == "b"
    assert top.kids[1].kids == []
    assert top.kids[0].kids[0].data == "a.a"






# ** speeding up linksets with cached tables
"""
If we know that the entire table is cached, we can speed
up linksets based on that table considerably.

The code that implements this is actually in LinkSetInjector.
"""
@testcase
def test_cached_linksets(test):

    class Parent(Strongbox):
        ID = attr(int)
        value = attr(str)
        kids = linkset((lambda : Child), "parent")

    class Child(Strongbox):
        ID = attr(int)
        value = attr(str)
        parent = link(Parent)

    child_table = 'ct'
    parent_table = 'pt'
    schema = Schema({
        Parent : parent_table,
        Child  : child_table,
        Child.parent : "parentID",
    })

    storage = RamStorage()
    clerk = Clerk(storage, schema)

    # set up our data:
    
    storage.store(parent_table, value='big_daddy')
    
    storage.store(child_table, value='a', parentID=0)
    storage.store(child_table, value='b', parentID=1)
    storage.store(child_table, value='c', parentID=1)
    storage.store(child_table, value='d', parentID=0)


    # Note: we could do this first:
    # big_daddy = clerk.fetch(Parent, 1)
    # *BUT* there used to be a case where
    # doing this first caused the test to pass
    # and doing it later caused the test to fail.
    # so... do it later to expose the bug.


    # cache it:
    clerk.cacheAll(Child)

    assert Parent.kids.back =="parent"
    assert Parent.kids.type == Child
    assert Child in clerk.cache.allCached
    assert Child not in clerk.cache.index

    # delete the underlying data, so there's no confusion
    for x in range(1,5):
        storage.delete(child_table, x)

    # grab the parent:
    big_daddy = clerk.fetch(Parent, 1)

    # note the parent is a stub:
    assert big_daddy.private.value == ''
    assert len(big_daddy.private.kids)==0
   

    # the stub is associated with the cached child objects
    test.assertEquals(4, len(clerk.cache.data[Child].values()))
    child2 = clerk.cache.data[Child][2]
    assert child2.parent is big_daddy


    # the stub should have two injectors:
    # a linkinjector (to fill in its own data)
    # and a linkset injector (for .kids)
    test.assertEquals(2, len(big_daddy.private.injectors))


    # now this should pull the data out of the cache:
    test.assertEquals(2, len(big_daddy.kids))


    # but note that it is *still* a stub!!
    assert big_daddy.private.value == ''


# ** indexing the cache by a column
"""
The above is all well and good, but if the underlying
database has an index on the foreign key, it's probably
got very near an O(1) lookup, and and our lookups are
going to be O(n) because we're looping through n records
every time we build a linkset.

We need to do what the database does, and index the cache.
"""
@addMethod(ClerkTest)
def test_cache_hash(self):

    self.storage.store(NODE_TABLE, data='root', parentID=0)
    self.storage.store(NODE_TABLE, data='1a', parentID=1)
    self.storage.store(NODE_TABLE, data='1b', parentID=1)
    self.storage.store(NODE_TABLE, data='1c', parentID=1)
    self.storage.store(NODE_TABLE, data='2a', parentID=2)
    self.storage.store(NODE_TABLE, data='2b', parentID=2)
    self.storage.store(NODE_TABLE, data='2c', parentID=2)

    self.clerk.cacheAll(Node, index=['data','parent'])

    n1a = self.clerk.cache.index[Node]['data']['1a'][0]
    assert n1a.data == '1a'

    p1 = n1a.parent
    assert p1.ID == 1
    
    #import pdb; pdb.set_trace()
    self.assertEquals(3, len(self.clerk.cache.index[Node]['parent'][p1.ID]))
    


# ** linksetinjectors and the cache
"""
Here we're doing the same thing as test_linkset_injection
and test_cached_linkset_injection, but now, we're going to
index the .parent backlink.

Why would indexing potentially make a difference?

Well, the LinkSetInjector takes a completely different execution
path when the field in question is indexed: instead of searching
through the cached table, it goes directly to the index.

"""

@addMethod(ClerkTest)
def test_indexed_linkset_injection(self):
    self.storage.store(NODE_TABLE, data="top", parentID=None)
    self.storage.store(NODE_TABLE, data="a",   parentID=1)
    self.storage.store(NODE_TABLE, data="a.a", parentID=2)
    self.storage.store(NODE_TABLE, data="b",   parentID=1)

    # cache and drop table
    self.clerk.cacheAll(Node, index=['parent'])
    self.storage.delete(NODE_TABLE, 1)
    self.storage.delete(NODE_TABLE, 2)
    self.storage.delete(NODE_TABLE, 3)
    self.storage.delete(NODE_TABLE, 4)

    index = self.clerk.cache.index[Node]['parent']

    # the index should have keys for each parentID
    assert type(index) is dict
    assert 1 in index
    assert 2 in index
    assert 3 not in index
    assert None in index # though we should probably use 0

    # the index should have two entries:
    assert len(index[1]) == 2
    assert index[1][0].data == 'a'
    assert index[1][1].data == 'b'

    # and that's exactly what we want when we ask for top.kids
    top = self.clerk.fetch(Node, 1)
    assert top.kids[0].data == "a"
    assert top.kids[1].data == "b"
    assert top.kids[1].kids == []
    assert top.kids[0].kids[0].data == "a.a"

    

# * callbacks
"""
Callbacks allow you to fire off arbitrary code whenever
you store an instance of a particular class.

For example, one application of this is to add the object's
content to a secondary data store (such as a local search
engine index).
"""

@testcase
def test_callbacks(self):

    class Thing(Strongbox):
        ID = attr(int)
        x = attr(str)

    class OtherThing(Strongbox):
        ID = attr(int)
        x = attr(str)

    queue = []
    schema = Schema({
        Thing: "thing",
        OtherThing: "other",
    })

    clerk = CallbackClerk(RamStorage(), schema)
    clerk.onStore(Thing, queue.append)

    clerk.store(Thing(x="a"))
    clerk.store(Thing(x="b"))
    clerk.store(OtherThing(x="not me"))


    queue2 = []
    clerk.onStore(Thing, queue2.append)
    clerk.store(Thing(x="c"))

    # "c" should wind up in both:
    assert len(queue) == 3
    assert "".join([t.x for t in queue]) == "abc"

    assert len(queue2) == 1
    assert queue2[0].x=="c"



# * schema objects
"""
The Schema class has a number of utility methods
used internally by the clerks module:
"""

@testcase
def test_schema(self):

    class Loop(Strongbox):
        next = link(lambda : Loop)
        tree = linkset((lambda : Loop), "next")

    s = Schema({
        Loop: "loop_table",
        Loop.next: "nextID",
    })
    assert s.tableForClass(Loop) == "loop_table"
    assert s.columnForLink(Loop.next) == "nextID"

    # it should be smart enough to infer the
    # links, but note that first have to clear out
    # the lambdas by actually instantiating a Loop
    # @TODO: should schema clear the lambda for us?
    x = Loop()
    assert s.tableForLink(Loop.next) == "loop_table"
    assert s.tableForLinkSet(Loop.tree) == "loop_table"
    assert s.columnForLinkSet(Loop.tree) == "nextID"



# * appendix: regression tests
"""
These are some more complicated tests and scenarios that
exposed bugs in the past.
"""

@testcase
def disappearing_events_regression_test(self):
    """
    This bug came from duckbill. A subscription
    would post events to its account, and then
    when it showed the statement, the new events
    would be the only ones to show up - even though
    there were still others in the database.

    Turns out the problem was that the sub.account
    stub didn't have injectors on ITS dependent
    objects. That's why I now replace .private
    in LinkInjector.inject()
    """
    class Evt(Strongbox):
        ID = attr(int)
        evt = attr(str)
        acc = link(lambda : Acc)
    class Sub(Strongbox):
        ID = attr(int)
        acc = link(lambda : Acc)
    class Acc(Strongbox):
        ID = attr(int)
        subs = linkset(Sub, "acc")
        evts = linkset(Evt, "acc")
    schema = Schema({
        Evt:"evt",
        Sub:"sub",
        Acc:"acc",
        Evt.acc: "accID",
        Sub.acc: "accID",
    })
    st = RamStorage()
    c1 = Clerk(st, schema)

    # store an account with two events and one sub:
    a = Acc()
    a.evts << Evt(evt="1")
    a.evts << Evt(evt="2")
    assert a.private.isDirty
    a.subs << Sub()
    c1.DEBUG = 1
    c1.store(a)

    # new clerk, new cache:
    c2 = Clerk(st, schema)

    # add more events while s.acc is a stub
    s = c2.fetch(Sub, ID=1)
    assert s.private.isDirty==False
    assert len(s.acc.evts) == 2, [e.evt for e in s.acc.evts]
    s.acc.evts << Evt(evt="3")
    #assert len(s.acc.evts) == 1, [e.evt for e in s.acc.evts]
    assert len(s.acc.evts) == 3, [e.evt for e in s.acc.evts]
    c2.DEBUG = 0
    c2.store(s)
    a2 = c2.fetch(Acc, ID=a.ID)

    assert a is not a2

    # we should now have all three events,
    # but we were getting only the third one:
    assert len(a2.evts) == 3, [e.evt for e in a2.evts]
    

@testcase
def complex_recursion_regression_test(self):
    """
    test case from cornerhost that exposed a bug.

    Basically it sets up several classes that refer
    to each other in a loop and makes sure it's
    possible to save them without infinite recursion.

    @TODO: isInstance(LinkSetInjector) in Clerk.py
    needs tests It ought to do some kind of polymorphism
    magic anyway.

    @TODO: huh?? :)
    """

    class User(Strongbox):
        ID = attr(int)
        username = attr(str)
        domains = linkset((lambda : Domain),"user")
        sites = linkset((lambda : Site),"user")
    class Domain(Strongbox):
        ID = attr(int)
        user = link(User)
        name = attr(str)
        site = link(lambda : Site)            
    class Site(Strongbox):
        ID = attr(int)
        user = link(User)
        domain = link(Domain)
    dbMap = Schema({
        User:"user",
        Domain:"domain",
        Domain.user: "userID",
        Domain.site: "siteID",
        Site:"site",
        Site.user: "userID",
        Site.domain: "domainID",
    })

    clerk = Clerk(RamStorage(), dbMap)
    u = clerk.store(User(username="ftempy"))
    u = clerk.match(User,username="ftempy")[0]
    d = clerk.store(Domain(name="ftempy.com", user=u))
    assert d.user, "didn't follow link before fetch"
    d = clerk.match(Domain, name="ftempy.com")[0]

    # the bug was here: it only happened if User had .domains
    # I think because it was a linkset, and the linkset had
    # an injector. Fixed by inlining the injector test into
    # Clekr.store:
    assert d.user, "didn't follow link after fetch"
    assert d.user.ID == u.ID

    # ah, but then we had an infinite recursion problem
    # with site, but I fixed that with private.isDirty:
    d.site = clerk.store(Site(domain=d))
    d = clerk.store(d)
    assert d.site.domain.name == "ftempy.com"

    # and again here:
    d = clerk.fetch(Domain, 1)
    assert not d.private.isDirty
    assert not d.site.private.isDirty # this failed.
    clerk.store(d)                    # so this would recurse forever



@testcase
def dirty_stub_regression(self):
    """
    Here's a situation where we have a stub in memory
    and we're modifying the stub.

    That should be fine, except at one point, writing to
    the stub didn't fill in the stub first. It should!
    
    You want to fetch the old data, THEN merge in the new data,
    so you can save the entire record to the database.

    Problem was that we weren't firing off injectors for
    strongbox.onSet()
    """
    class Other(Strongbox):
        ID = attr(int)
        fname = attr(str)
        mname = attr(str)
        lname = attr(str)
        things = linkset((lambda: Thing), "other")
        
    class Thing(Strongbox):
        ID = attr(int)
        other = link(Other)
        data = attr(str)
        
    dbMap = Schema({Thing: "thing", Other: "other", Thing.other: "otherID"})
    store = RamStorage()
    
    clerkA = Clerk(store, dbMap)
    top = Other(fname="wanda", mname="jane", lname="tempy")
    top.things << Thing(data="abc")
    clerkA.store(top)
    del clerkA

    clerkB = Clerk(store, dbMap)
    thing = clerkB.fetch(Thing, 1)
    other = thing.other
    assert other.private.isStub
    assert not other.private.isDirty

    other.fname = "fred"
    assert other.private.isDirty
    assert not hasattr(other.private, "isStub"), "uh-oh. a dirty stub!"

    other.mname = "patrick"

    # and of course we still want the change to go through!
    assert other.lname == "tempy"
    assert other.fname == "fred"
    assert other.mname == "patrick"
    

# * unit test runner

if __name__=="__main__":
    unittest.main()
