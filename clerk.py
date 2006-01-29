# arlo: consolidated version.
"""
clerk: an object-relational mapper in literate style
"""
from pytypes import IdxDict
from strongbox import *
from storage import where
from __future__ import generators
import operator
from unittest import TestCase
from storage import MockStorage

# * introduction
"""
At a high level, what we're doing here is moving data back and forth
between python objects and some kind of external storage. Generally
a database.

This is somewhat unusual compared to other systems - like SQLObject.
Why not just let the objects talk to the database directly? Well,
the main idea is that sometimes, especially for testing, you want
to create objects that don't live in the database. I used to use
records that were tightly bound to the database, but I found it
was easier to just use one "Clerk" object.

"""
# * Lazyloading with Injectors
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
object and it will know it's ID, and can therefore load its projects
without ever reading the manager data from the database!!

What about the tree explosion? Well, you can just read the
whole table at once up front...



302 stopped to fold laundry ----- [0116.2006 03:02PM]

"""
# ** LinkInjector
# *** test
class Foreign(Strongbox):
    ID = attr(long)
    data = attr(str)

class Local(Strongbox):
    ref = link(Foreign)


class LinkInjectorTest(TestCase):

    def check_inject(self):
        """
        basic test case.
        """
        schema = Schema({
            Foreign: "foregin",
            Local: "local",
            Local.ref: "foreignID",
        })
        clerk = MockClerk(schema)
        
        obj = Local()
        assert obj.ref is None

        clerk.store(Foreign(data="Here I come to save the day!"))

        obj.ref = Foreign(ID=1)
        obj.ref.addInjector(LinkInjector(clerk, Foreign, 1).inject)
        assert len(obj.ref.private.injectors) == 1

        # should be able to fetch the ID without triggering load
        assert obj.ref.ID == 1
        assert obj.ref.private.data == ""
        assert len(obj.ref.private.injectors) == 1

        # but getting any other field triggers the load!
        assert obj.ref.data == "Here I come to save the day!"
        assert len(obj.ref.private.injectors) == 0


    def check_with_linkset(self):
        """
        what happens if the thing we're injecting
        has a linkset of its own (this used to fail)
        """

        class Kid(Strongbox):
            ID = attr(long)
            parent = link(forward)
        
        class Parent(Strongbox):
            ID = attr(long)
            name = attr(str)
            kids = linkset(Kid, "parent")
            
        Kid.parent.type = Parent
        
        class Uncle(Strongbox):
            brother = link(Parent)

        schema = Schema({
            Kid: "kid",
            Kid.parent: "parentID",
            Parent: "parent",
            Uncle: "uncle",
            Uncle.brother: "brotherID",
        })
        clerk = MockClerk(schema)


        kid = Kid()
        dad = Parent(name="Brother Dad")
        dad.kids << kid
        clerk.store(dad)
        
        unc = Uncle()
        unc.brother = Parent(ID=1)
        unc.brother.addInjector(LinkInjector(clerk, Parent, 1).inject)

        ## this next line threw an AttributeError because the
        ## injector tried to include "kids" in the .update() call
        assert unc.brother.name=="Brother Dad"
# *** code
class LinkInjector:
    def __init__(self, clerk, fclass, fID):
        """
        Registers a callback so that when getattr(box, atr)
        is called, the object of box.atr's type with given ID
        is loaded from sto and injected into box.

        In other words, this provides lazy loading for
        strongboxen.
        """
        self.clerk = clerk
        self.fID = fID
        self.fclass = fclass

    def inject(self, stub, name):
        """
        This injects data into the stub.

        WARNING: It replaces the entire .private
        object with a fresh instance, which means any
        state information will disappear. That is why
        it's imperative that you call .notifyInjectors()
        before manipulating .private in your Strongbox.

        However, it does preserve observers and
        any other injectors attached to the stub.
        """
        if name == "ID":
            pass # stubs have ID, so no need to load
        else:
            old = stub.private

            # we call fetch so we get stubs for all the
            # new object's dependents
            new = self.clerk.fetch(self.fclass, self.fID).private

            # inject the data:
            for slot in self.fclass.__attrs__:
                setattr(old, slot, getattr(new, slot))
            old.isDirty = False

            # since we might have observers, we'll
            # let them know:
            stub.notifyObservers("inject", "inject")
            stub.removeInjector(self.inject)
# ** LinkSetInjector
# *** test
class Content(Strongbox):
    ID = attr(long)
    box = link(forward)
    data = attr(str)

class Package(Strongbox):
    ID = attr(long)
    refs = linkset(Content, "box")

Content.box.type=Package

class LinkSetInjectorTest(TestCase):

    def check_inject(self):

        ms = MockStorage()
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
# *** code
class LinkSetInjector:
    def __init__(self, atr, clerk, fclass, fkey):
        """
        atr: the attribute name for the linkset
        clerk: a clerk
        fclass: the type of the linkset
        fkey: column name of the foreign key that points back to the parent
        """
        self.clerk = clerk
        self.atr = atr
        self.fclass = fclass
        self.fkey = fkey

    def inject(self, box, name):
        """
        box: the Strongbox instance we're being called from
        name: the attribute name that was getattr'd
        """
        if name == self.atr:
            box.removeInjector(self.inject)
            table = self.clerk.schema.tableForClass(self.fclass)
            for row in self.clerk.storage.match(table, **{self.fkey:box.ID}):
                obj = self.clerk.rowToInstance(row, self.fclass)
                getattr(box.private, self.atr) << obj



# * ClerkError
class ClerkError(Exception): pass

# * getSlotsOfType
def getSlotsOfType(klass, t):
    for slot in klass.__attrs__:
        attr = getattr(klass, slot)
        if isinstance(attr, t):
            yield (slot, attr)



# * BoxInspector 
class BoxInspector(object):
    def __init__(self, box):
        self.box = box
    def plainValues(self):
        """
        returns a dict of name:value pairs
        with one enty per plain attribute
        """
        res = {}
        for item in self.plainAttributes():
            res[item] = getattr(self.box, item)
        return res
    def plainAttributes(self):
        """
        returns a list of plain attribute
        names  on the box:  Attributes, but not
        links, linksets, or virtual properties
        """
        return [
            name
            for (name,value) in self.box.__attrs__.items()
            if type(value) == attr
        ]
    def linkNames(self):
        return getSlotsOfType(self.box.__class__, link)



# * Schema
# ** test
class Loop(Strongbox):
    next = link(forward)
    tree = linkset(forward, "next")
Loop.next.type = Loop
Loop.tree.type = Loop

class SchemaTest(unittest.TestCase):

    def test_schema(self):
        s = Schema({
            Loop: "loop_table",
            Loop.next: "nextID",
        })
        assert s.tableForClass(Loop) == "loop_table"
        assert s.columnForLink(Loop.next) == "nextID"

        # it should be smart enough to infer these:
        assert s.tableForLink(Loop.next) == "loop_table"
        assert s.tableForLinkSet(Loop.tree) == "loop_table"
        assert s.columnForLinkSet(Loop.tree) == "nextID"
# ** code
class Schema(object):
    def __init__(self, dbmap=None):
        """
        optionally takes a dict that maps
        strongbox.*Box classes to tables
        and strongbox.Link instances to 
        columns
        """
        self.dbmap = {}
        if dbmap:
            self.dbmap.update(dbmap)

    # these two are given explictly:
    def tableForClass(self, klass):
        return self.dbmap[klass]
    def columnForLink(self, ln):
        return self.dbmap[ln]

    # the rest are inferred:
    def tableForLink(self, ln):
        return self.tableForClass(ln.type)
    def tableForLinkSet(self, ls):
        return self.tableForClass(ls.type)
    def columnForLinkSet(self, ls):
        return self.columnForLink(getattr(ls.type, ls.back))
# * AutoSchema (??)

## class AutoSchema(object): # @TODO: make this class
##     """
##     Automatically maps objects to tables,
##     and Links to foreign key names.
##     """
##     def __getitem__(self, item):
##         if isinstance(item, link):
##             return item.type, item.__name__ + "ID"
##         elif isinstance(item, linkset):
##             assert item.back, "no .back found for %s.%s" \
##                    % (item.__owner__.__name__ , item.__name__)
##             return item.back.__name__ + "ID"
##         else:
##             return item.__name__

## @TODO: need to put item.__name__ on links
## ... also see if the keyerror throws the
## classname so I don't have to do "no mapping found for ..."
        
##     def _unmap_class(self, klass):
##         if klass in self:
##             return self[klass]
##         else:
##             return klass.__name__

##     def _unmap_link(self, klass, lnk, name):
##         try:
##             return self[lnk]
##         except KeyError:
##             raise ClerkError, "no mapping found for %s.%s" \
##                   % (klass.__name__, name)


# * Clerk
# ** test
class Record(Strongbox):
    ID = attr(long)
    val = attr(str)
    next = link(forward)
Record.next.type=Record

class Node(Strongbox):
    ID = attr(long)
    data = attr(str)
    parent = link(forward)
    kids = linkset(forward, "parent")
Node.kids.type=Node
Node.parent.type=Node   

class ClerkTest(unittest.TestCase):

    def setUp(self):
        self.storage = MockStorage()
        schema = Schema({
            Node: "Node",
            Node.parent: "parentID",
            Record: "Record",
            Record.next: "nextID",
        })
        self.clerk = Clerk(self.storage, schema)


    def test_store(self):
        self.clerk.store(Record())
        actual = self.storage.match("Record")
        assert actual == [{"ID":1, "val":"", "nextID":0}], actual
        r = self.clerk.fetch(Record, 1)
        assert r.next is None
        

    def test_store_again(self):
        self.clerk.store(Record())
        r = self.clerk.fetch(Record, 1)
        r.val = "abc"
        self.clerk.store(r)

    def test_store_link(self):
        r = Record(val="a")
        r.next = Record(val="b")

        self.clerk.store(r)
        del r
        r = self.clerk.match(Record, val="a")[0]
        assert r.ID == 2, "didn't save links first!"
        assert r.next is not None, "didn't store the link"
        assert r.next.val=="b", "didn't store link correctly"

        r.next = None
        self.clerk.store(r)
        r = self.clerk.match(Record, val="a")[0]
        assert r.next is None, "didn't delete link!"

        r = Record(val="noNext")
        self.clerk.store(r)
        r = self.clerk.fetch(Record, val="noNext")
        assert r.next is None


    def test_store_memo(self):
        rb = self.clerk.store(Record(val="b"))
        ra = self.clerk.store(Record(val="a", next=rb))

        a,b = self.clerk.match(Record, orderBy="val")
        assert a is ra
        assert b is rb


    def test_store_linksets(self):
        n1 = Node(data="a")
        n1.kids << Node(data="aa")
        n1.kids << Node(data="ab")
        n1.kids[1].kids << Node(data="aba")
        self.clerk.store(n1)
        assert len(n1.kids)== 2, [(k.ID, k.data) for k in n1.kids]        
        
        n = self.clerk.fetch(Node, data="a")
        assert len(n1.kids)== 2, "fetch corrupted kids: %s" % [(k.ID, k.data) for k in n1.kids]
        
        assert n.ID == 1, "didn't save parent of linkset first!"
        assert len(n.kids)== 2, "didn't store the linkset: %s" % [(k.ID, k.data) for k in n.kids]
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

        
        
    def test_fetch(self):
        self.clerk.store(Record(val="howdy"))

        # we can pass in an ID:
        obj = self.clerk.fetch(Record, 1)
        assert obj.val == "howdy"

        # or we can use keywords:
        obj = self.clerk.fetch(Record, val="howdy")
        assert obj.val == "howdy"


    def test_delete(self):
        self.test_fetch()
        self.clerk.delete(Record, 1)
        assert self.storage.match("Record") == []


    def test_link_injection(self):
        self.storage.store("Record", val="a", nextID=2)
        self.storage.store("Record", val="b", nextID=3)
        self.storage.store("Record", val="c", nextID=None)

        a = self.clerk.fetch(Record, 1)
        
        assert a.val == "a"
        assert a.next.val == "b"
        assert a.next.next.val == "c"
        assert a.next.next.next is None


    def test_linkset_injection(self):
        self.storage.store("Node", data="top", parentID=None)
        self.storage.store("Node", data="a",   parentID=1)
        self.storage.store("Node", data="a.a", parentID=2)
        self.storage.store("Node", data="b",   parentID=1)
        
        top = self.clerk.fetch(Node, 1)
        assert top.kids[0].data == "a"
        assert top.kids[1].data == "b"
        assert top.kids[1].kids == []
        assert top.kids[0].kids[0].data == "a.a"

        

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
            self.storage.store("Record", val="a", extra_column="EEK!")
            a = self.clerk.fetch(Record, 1)
            a.val="aa"
            self.clerk.store(a)
        except AttributeError:
            self.fail("shouldn't die when columns outnumber attributes")

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


    def test_recursion(self):
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
        
        
    def test_identity(self):
        self.clerk.store(Record(val="one"))
        rec1a = self.clerk.fetch(Record, 1)
        rec1b = self.clerk.fetch(Record, 1)
        assert rec1a is rec1b

        n = Record()
        r = Record(next=n)        
        assert self.clerk.store(r) is r
        assert self.clerk.cache[(Record, r.ID)] is r
        assert self.clerk.cache[(Record, n.ID)] is n
        assert self.clerk.cache[(Record, n.ID)] is r.next

    def test_stub(self):
        self.clerk.store(Record(val="a", next=Record(val="b")))
        self.clerk.cache.clear()
        recA = self.clerk.fetch(Record, val="a")
        recB = self.clerk.fetch(Record, val="b")
        assert recA.next.ID == recB.ID
        assert recA.next is recB

    def test_match(self):
        self.clerk.store(Record(val="one"))
        self.clerk.store(Record(val="two"))
        self.clerk.store(Record(val="two"))
        assert len(self.clerk.match(Record, val="zero")) == 0
        assert len(self.clerk.match(Record, val="one")) == 1
        assert len(self.clerk.match(Record, val="two")) == 2
        
    def test_matchOne(self):
        self.clerk.store(Record(val="one"))
        self.clerk.store(Record(val="two"))
        self.clerk.store(Record(val="two"))
        
        try:
            self.clerk.matchOne(Record, val="zero")
            self.fail("should have failed for not matching")
        except LookupError: pass

        assert isinstance(self.clerk.matchOne(Record, val="one"),
                          Record)

        try:
            self.clerk.matchOne(Record, val="two")
            self.fail("should have failed for matching two")
        except LookupError: pass
        

# ** code
class Clerk(object):
    __ver__="$Id: Clerk.py,v 1.28 2004/11/11 05:51:52 sabren Exp $"
    """
    Clerk is an object-relational mapper, responsible
    for storing strongbox-style objects in storage
    systems defined with the 'storage' module.

    Constructor is: Clerk(storage) or Clerk(storage, dbmap)
    where dbmap is a dictionary mapping classes to table names.
    """

    def __init__(self, storage, schema):
        self.storage = storage
        self.schema = schema
        
        # so we always return same instance for same row:
        # @TODO: WeakValueDictionary() doesn't work with strongbox. Why?!
        self.cache = {}

    ## public interface ##############################################
        
    def store(self, obj):
        """
        This traverses the object graph recursively,
        storing changed objects. 
        """
        self._seen = {}
        return self._recursive_store(obj)



    def _recursive_store(self, obj):

        # this ensures that we process each object only once
        # while we traverse the object graph
        if obj in self._seen:
            return obj
        self._seen[obj] = True

        # this just gets data about the object. @TODO: might be out of date
        insp = BoxInspector(obj)
        vals = insp.plainValues()
        klass = obj.__class__

        #if hasattr(self, "DEBUG"):
        #    print "storing %s(ID=%s)" % (klass.__name__, obj.ID)

        # we need to save links first, because we depend on them:
        for name, lnk in insp.linkNames():
            column = self.schema.columnForLink(lnk)
            ref = getattr(obj, name)
            if (ref):
                # here is where we traverse the links:
                vals[column] = self._recursive_store(ref).ID
            else:
                vals[column] = 0

        # now we update obj because of db-generated values
        # (such as autonumbers or timestamps)
        if hasattr(obj, "ID"): old_id = obj.ID
        if obj.private.isDirty:
            # then store the data:
            data_from_db = self.storage.store(self.schema.tableForClass(klass), **vals)
            relevant_columns = self._attr_columns(klass, data_from_db)
            obj.update(**relevant_columns)
        id_has_changed = hasattr(obj,"ID") and (obj.ID != old_id)

        # this next bit is tricky.
        #
        # dont_need_injectors is there so that stubs can
        # live happily in the cache and can be updated by
        # rowToInstance without getting yet another set of
        # injectors added on. However, fresh objects that
        # have never been stored should ALSO not have
        # injectors (because all their data will be fresh
        # or already processed by the clerk)... Since there's
        # no other place to detect fresh objects, I put this
        # here. I have a hunch that changing this to
        # .need_injectors instead might simplify the logic
        # considerably but this is working and at the moment
        # I don't feel like changing it. :)
        # @TODO: .dont_need_injectors => .need_injectors
        if id_has_changed:
            obj.private.dont_need_injectors = True
            
        # we've got the clean data, but we called update
        # with the new primary key,  so we need to reset
        # isDirty. We have to do it before linkset stuff
        # to prevent infinite recursion on cyclic data
        # structures.
        obj.private.isDirty = False

        # linkSETS, on the other hand, depend on us, so they go last:
        for name, ls in getSlotsOfType(klass,linkset):
            column = self.schema.columnForLinkSet(ls)
            for item in getattr(obj.private, name):
                if id_has_changed:
                    item.private.isDirty = True
                    assert getattr(item, ls.back) is obj, \
                       "getattr(%s, %s) was not (this) %s" \
                       % (item.__class__.__name__, ls.back, obj.__class__.__name__)
                self._recursive_store(item)

        self._put_memo(obj)
        return obj



    def rowToInstance(self, row, klass):
        attrs, othercols = self._attr_and_other_columns(klass, row)
        obj = self._get_memo(klass, attrs.get("ID"))
        if obj:
            # refresh data, but don't break the cache:
            obj.update(**attrs)
        else:
            obj = klass(**attrs)
        if not hasattr(obj.private, "dont_need_injectors"):
            self.addInjectors(obj, othercols)
        self._put_memo(obj)
        obj.private.isDirty = 0
        return obj


    def match(self, klass, *args, **kwargs):
        return [self.rowToInstance(row, klass)
                for row in self.storage.match(self.schema.tableForClass(klass),
                                              *args, **kwargs)]

    def matchOne(self, klass, *arg, **kw):
        res = self.match(klass, *arg, **kw)
        if len(res)==0:
            raise LookupError("matchOne(%s, *%s, **%s) didn't match anything!"
                              % (klass, arg, kw))
        elif len(res)>1:
            raise LookupError("matchOne(%s, *%s, **%s) matched %s objects!"
                              % (klass, arg, kw, len(res)))
        return res[0]
 
    def fetch(self, klass, __ID__=None, **kw):
        if __ID__:
            return self.matchOne(klass, ID=__ID__)
        else:
            return self.matchOne(klass, **kw)

    def delete(self, klass, ID): #@TODO: ick!!
        self.storage.delete(self.schema.tableForClass(klass), ID)
        return None


    ### private stuff ###############################################

    def _get_memo(self, klass, key):
        uid = (klass, key)
        return self.cache.get(uid)

    def _put_memo(self, obj):
        if hasattr(obj, "ID"):
            self.cache[(obj.__class__, obj.ID)]=obj
        else:
            raise Warning("couldn't memo %s because it had no ID attribute" % obj)

    def addInjectors(self, obj, othercols):
        obj.private.dont_need_injectors = True
        klass = obj.__class__
        ## linkinjectors:
        for name,lnk in getSlotsOfType(klass,link):
            fclass = lnk.type
            column = self.schema.columnForLink(lnk)
            fID = othercols.get(column)
            if fID:
                memo = self._get_memo(fclass, fID)
                if memo:
                    setattr(obj, name, memo)
                else:
                    stub = fclass(ID = fID)
                    stub.private.isDirty = 0
                    stub.addInjector(LinkInjector(self, fclass, fID).inject)
                    setattr(obj, name, stub)
                    self._put_memo(stub)

        ## linksetinjectors:
        for name,ls in getSlotsOfType(klass,linkset):
            fclass = ls.type
            column = self.schema.columnForLinkSet(ls)
            #@TODO: there can just be one LSI instance per linkset attribute
            #(since it no longer keeps its own reference to the object)
            obj.addInjector(LinkSetInjector(name, self, fclass, column).inject)

    def _attr_columns(self, klass, rec):
        return self._attr_and_other_columns(klass, rec)[0]

    def _attr_and_other_columns(self, klass, rec):
        attrs, others = {}, {}
        for item in rec.keys():
            if item in klass.__attrs__:
                attrs[item]=rec[item]
            else:
                others[item]=rec[item]
        return attrs, others

# * CallbackClerk
# ** test
class Thing(Strongbox):
    ID = attr(long)
    x = attr(str)

class OtherThing(Strongbox):
    ID = attr(long)
    x = attr(str)

class CallbackClerkTest(unittest.TestCase):

    def test_onStore(self):
        queue = []
        schema = Schema({
            Thing: "thing",
            OtherThing: "other",
        })
            
        clerk = CallbackClerk(MockStorage(), schema)
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
# ** code
class CallbackClerk(Clerk):
    """
    This class allows you to set up callbacks
    to trigger events whenever an object of a
    particular class gets stored.
    """

    def __init__(self, *args, **kwargs):
        super(CallbackClerk, self).__init__(*args, **kwargs)
        self._callbacks = {}       
    
    def onStore(self, klass, dowhat):
        self._callbacks.setdefault(klass,[])
        self._callbacks[klass].append(dowhat)
        
    def store(self, thing):
        thing = super(CallbackClerk, self).store(thing)
        klass = thing.__class__
        for callback in self._callbacks.get(klass, []):
            callback(thing)
        return thing


# * MockClerk
def MockClerk(dbmap=None):
    return Clerk(MockStorage(), dbmap or AutoSchema())

# * regression test
class _regression_Test(unittest.TestCase):

    def test_disappearing_events(self):
        """
        This bug came from duckbill. A subscription
        would post events to its account, and then
        when it showed the statements the new events
        would be the only ones to show up - even though
        there were still others in the database.

        In other words, the injector wasn't working.

        Turns out the problem was that the sub.account
        stub didn't have injectors on ITS dependent
        objects. That's why I now replace .private
        in LinkInjector.inject()
        """
        class Evt(Strongbox):
            ID = attr(long)
            evt = attr(str)
            acc = link(forward)
        class Sub(Strongbox):
            ID = attr(long)
            acc = link(forward)
        class Acc(Strongbox):
            ID = attr(long)
            subs = linkset(Sub, "acc")
            evts = linkset(Evt, "acc")
        Evt.acc.type = Acc
        Sub.acc.type = Acc
        schema = Schema({
            Evt:"evt",
            Sub:"sub",
            Acc:"acc",
            Evt.acc: "accID",
            Sub.acc: "accID",
        })
        st = MockStorage()
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
        assert not s.private.isDirty
        #@TODO: maybe len() should trigger the lazyload...
        assert len(s.acc.evts) == 0, [e.evt for e in s.acc.evts]
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
    

    def test_complex_recursion(self):
        """
        test case from cornerhost that exposed a bug.
        this is probably redundant given test_recursion
        but it doesn't hurt to keep it around. :)

        This test is complicated. Basically it sets up
        several classes that refer to each other in a loop
        and makes sure it's possible to save them without
        infinite recursion.
        
        @TODO: isInstance(LinkSetInjector) in Clerk.py need tests
        It ought to do some kind of polymorphism magic anyway.
        (huh??)
        """

        class User(Strongbox):
            ID = attr(long)
            username = attr(str)
            domains = linkset(forward,"user")
            sites = linkset(forward,"user")
        class Domain(Strongbox):
            ID = attr(long)
            user = link(User)
            name = attr(str)
            site = link(forward)            
        class Site(Strongbox):
            ID = attr(long)
            user = link(User)
            domain = link(Domain)
        User.domains.type = Domain
        User.sites.type = Site
        Domain.site.type = Site
        dbMap = Schema({
            User:"user",
            Domain:"domain",
            Domain.user: "userID",
            Domain.site: "siteID",
            Site:"site",
            Site.user: "userID",
            Site.domain: "domainID",
        })
       
        clerk = Clerk(MockStorage(), dbMap)
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


# * --
if __name__=="__main__":
    unittest.main()
