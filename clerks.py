# arlo: consolidated version.
"""
clerk: an object-relational mapper
"""
import operator
from strongbox import *
from storage import where
from storage import MockStorage

class _EMPTY_LINK:
    """
    A Null Object that holds the ID when Link=None
    """
    ID = 0


def _linksAndValues(obj):
    """
    returns a list of (linkObject, refObject) pairs for the object.
    If value is None, returns _EMPTY_LINK, so that you can always
    use refObject.ID
    """
    return [(lnkObj, getattr(obj, name) or _EMPTY_LINK)
            for name, lnkObj in obj.getSlotsOfType(link)]

            # Q: Won't that getattr call fire off a database select?
            # A: Nope. Remember that these linked objects may be stubs
            # that only contain the ID. As long as we only look at ref.ID,
            # this won't load data un-necessarily.

class Cache(object):
    """
    Cache[klass][ID] = instance
    """
    def __init__(self):
        self.data = {}
        self.index = {}
        self.allCached = {}

    def __getitem__(self, (klass, ID)):
        # for the test cases
        return self.data[klass][ID]

    def __setitem__(self, (klass, ID), value):
        self.data.setdefault(klass, {})[ID] = value


    def markCached(self, klass):
        self.allCached[klass] = True 

    def clear(self):
        self.data.clear()


    def get(self, klass, key):
        try:
            return self.data[klass][key]
        except KeyError:
            return None

    def store(self, obj):
        if hasattr(obj, "ID"):
            self[(obj.__class__, obj.ID)]=obj
        else:
            raise Warning("couldn't memo %s because it had no ID attribute"
                          % obj)



class Clerk(object):
    """
    Clerk is an object-relational mapper, responsible
    for storing strongbox-style objects in storage
    systems defined with the 'storage' module.
    """

    def __init__(self, storage, schema):
        self.storage = storage
        self.schema = schema
        self.cache = Cache()


    def _addLinksAndStubs(self, obj, othercols):
        for name, lnk in obj.getSlotsOfType(link):
            fID = othercols.get(self.schema.columnForLink(lnk))
            if fID:
                setattr(obj.private, name,
                        (self.cache.get(lnk.type, fID)
                         or self._makeStub(lnk.type, fID)))
            else:
                pass # obj.whatever is None, so no stub/memo needed


    def _addLinkSetInjectors(self, obj):
        for name,ls in obj.getSlotsOfType(linkset):
            column = self.schema.columnForLinkSet(ls)
            #@TODO: there can just be one LSI instance per linkset attribute
            #(since it no longer keeps its own reference to the object)
            obj.addInjector(LinkSetInjector(name, self, ls, column).inject)


    def _makeStub(self, klass, ID):
        stub = klass(ID=ID)
        stub.private.isDirty = False
        stub.private.isStub = True
        stub.addInjector(LinkInjector(self, klass, ID).inject)
        self._addLinkSetInjectors(stub)
        self.cache.store(stub)
        return stub


    def _recursive_store(self, obj, seen):
 
        # this ensures that we process each object only once
        # while we traverse the object graph
        if obj in seen or obj is _EMPTY_LINK:
            return obj

        seen[obj] = True

        # Save linked Objects ####################################
        #
        # we need to save links first, because we depend on them.
        # for example:
        #
        #    parent.child = Child(val='whatever')
        #
        # we now want to store parent.childID but we can't
        # do that unless we store the child and get the
        # generated primary key.


        for _, ref in _linksAndValues(obj):
            self._recursive_store(ref, seen)

       
        # Save the main object ###################################

        self._store_one_instance(obj)


        # Save the LinkSETS. ####################################
        #
        # These objects depend on having the main object's ID
        # for the backlink, so they have to get saved last:
        #
        # Note that since we don't want to trigger a cascade
        # of fetches from the database only to turn around and
        # store the data again , we use object.private.xs rather
        # than object.xs
        #
        # @TODO: better explain the pro's/cons of using obj.private vs obj
        for name, ls in obj.getSlotsOfType(linkset):
            for item in getattr(obj.private, name):
                self._recursive_store(item, seen)

        return obj


    def _rowToInstance(self, row, klass):
        attrs, othercols = self._writable_and_other_columns(klass, row)

        
        cached = self.cache.get(klass, attrs.get("ID"))
        if cached:

            obj = cached

            # the rule: changes in ram trump changes is the DB
            # otherwise, you can make changes, think you're saving
            # them, and find out your changes were discarded. That
            # would be bad. So only update clean objects.
            
            # @TODO: write an explicit test to expose this condition
            # (it would happen if you have an object in ram and then load
            # it again - perhaps through some other objects linkset... and
            # of course if the code here didn't fix the problem. :))

            # if the object hasn't changed in ram, it's
            # okay to refresh the data. in fact, this
            # is required if the cached version is just
            # a stub!!
            if obj.private.isDirty == False:

                obj = cached
                obj.update(**attrs)
                # but now it is dirty, so mark it clean:
                obj.private.isDirty = False

            if hasattr(obj.private, 'isStub'):
                # The object is marked as a stub, but it's
                # not a stub anymore, because we just filled it in!
                # So we have to fix that.
                del obj.private.isStub

                # Also, since we have the foreign keys now
                # (in the othercols dict),  we need to take
                # this opportunity to add new stubs for all
                # the links attached to this object.
                
                # (We don't add linkSET injectors here
                # because stubs already have them)
                self._addLinksAndStubs(obj, othercols)


        else:
        
            # in here we're dealing with a brand new object
            obj = klass(**attrs)
            self.cache.store(obj)
            self._addLinksAndStubs(obj, othercols)
            self._addLinkSetInjectors(obj)
            obj.private.isDirty = False
                
        return obj



    def _store_one_instance(self, obj):

        if obj.private.isDirty:

            vals = obj.attributeValues()
            for lnkObj, ref in _linksAndValues(obj):
                vals[self.schema.columnForLink(lnkObj)]=ref.ID
            klass = obj.__class__
            data_from_db = self.storage.store(
                self.schema.tableForClass(klass), **vals)

            # update object w/db-generated values
            #(e.g., autonumbers or timestamps)
            obj.update(**self._writable_columns(klass, data_from_db))

            # since update marks the object dirty, undo that:
            obj.private.isDirty = False

            # and since this may be the first time we're seeing this
            # object (i.e., it may be the initial save of new data),
            # stick it in the cache:
            self.cache.store(obj)

        else:
            # object hasn't changed since we loaded it, so don't bother saving
            pass
                    

    def _writable_and_other_columns(self, klass, rec):
        """
        this separates the rec dictionary into two
        dictionaries:

        the first contains the key-value pairs for the attribute columns

        the second contains data from other columns that appear in
        the database but are not writable in the object itself.
        For example: calculated fields.
        """
        attrs, others = {}, {}
        #@TODO: listWritableSlots probably ought to be a classmethod
        writables = klass().listWritableSlots()
        for item in rec.keys():
            if item in writables:
                attrs[item]=rec[item]
            else:
                others[item]=rec[item]
        return attrs, others


    def _writable_columns(self, klass, rec):
        return self._writable_and_other_columns(klass, rec)[0]



    ## public interface ##############################################
        

    def cacheAll(self, klass, index=[]):
        """
        Acts like .match(klass) but also allows indexing the cache by columns.
        """
        if index:
            matches = self.match(klass)
            
            # cache the matches
            sci = self.cache.index
            for column in index:
                sci.setdefault(klass, {}).setdefault(column, {})

                
            for item in matches:
                for column in index:
                    # use item.private here so we don't trigger
                    # another query if the table is self-referential
                    # (because we might be loading a 
                    thing = getattr(item.private,column)
                    if hasattr(thing, "ID"): thing = thing.ID
                    sci[klass][column].setdefault(thing,[])
                    sci[klass][column][thing].append(item)

            return matches
        else:
            return self.match(klass)
       

    def delete(self, klass, ID): #@TODO: ick!!
        """
        Delete the instance of klass with the given ID
        """
        #@TODO: this needs to remove it from the cache!
        self.storage.delete(self.schema.tableForClass(klass), ID)
        return None


    def fetch(self, klass, __ID__=None, **kw):
        """
        Like matchOne, but lets you pass in a primary key.
        """
        if __ID__:
            assert not kw, "ID and where are mutually exclusive for fetch"
            return (self.cache.get(klass, __ID__)
                    or self.matchOne(klass, ID=__ID__))
        else:
            return self.matchOne(klass, **kw)


    def match(self, klass, *args, **kwargs):
        """
        Returns a list of matched objects.
        """
        if (klass in self.cache.allCached) and (not args):
            # @TODO: real where clauses for live objects
            matches = []
            for item in self.cache.data[klass].values():
                keepThisOne = True
                for k,v in kwargs.items():
                    if getattr(item, k) != v:
                        keepThisOne = False
                if keepThisOne: matches.append(item)
        else:
            matches = [self._rowToInstance(row, klass)
                       for row in self.storage.match(
                          self.schema.tableForClass(klass), *args, **kwargs)]
        if not (args or kwargs):
            self.cache.markCached(klass)
        return matches

    def matchOne(self, klass, *arg, **kw):
        """
        Like match, but ensures the query matches exactly one object.
        Throws a LookupError if 0 or more than one object matches.
        """
        res = self.match(klass, *arg, **kw)
        if len(res)==0:
            raise LookupError("matchOne(%s, *%s, **%s) didn't match anything!"
                              % (klass, arg, kw))
        elif len(res)>1:
            raise LookupError("matchOne(%s, *%s, **%s) matched %s objects!"
                              % (klass, arg, kw, len(res)))
        return res[0]


    def store(self, obj):
        """
        Store the object
        along with any linked objects marked with .isDirty = True.
        """
        return self._recursive_store(obj, seen={})





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



class ClerkError(Exception):
    """
    A generic error raised for problems related to clerk.
    """
    pass

    

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
        if name == "ID" or isinstance(getattr(stub.__class__, name), linkset):
            # stubs have .ID, so no need to load
            # same thing with linksets!
            pass 
        else:
            stub.removeInjector(self.inject)

            # The stub might not be a stub anymore!
            # A clerk.match() call might have filled it in.
            # So, check to make sure before we do anything.
            if hasattr(stub.private, 'isStub'):
                
                pri = stub.private

                # can't use the clerk directly here because 
                # fetch would just return the cached box! :)
                raw = self.clerk.storage.fetch(
                    self.clerk.schema.tableForClass(self.fclass),
                    self.fID)

                # inject the data:
                for slot in stub.listWritableSlots():
                    if slot in raw:
                        setattr(pri, slot, raw[slot])


                # now add the stubs to this object.
                attrs, othercols = self.clerk._writable_and_other_columns(
                    self.fclass, raw)
                self.clerk._addLinksAndStubs(stub, othercols)


                pri.isDirty = False

                # and, of course, we're not a stub anymore.
                del pri.isStub

                # finally, since we might have observers, we'll
                # let them know:
                stub.notifyObservers("inject", "inject")




class LinkSetInjector:
    
    def __init__(self, atr, clerk, linksetAttr, fkey):
        """
        atr: the attribute name for the linkset
        clerk: a clerk
        fclass: the type of the linkset
        fkey: column name of the foreign key that points back to the parent
        """
        self.clerk = clerk
        self.name = atr
        self.fkey = fkey
        self.linksetAttr = linksetAttr

    def inject(self, box, name):
        """
        box: the Strongbox instance we're being called from
        name: the attribute name that was getattr'd
        """
        if name == self.name:
            box.removeInjector(self.inject)

            # here we're using the class attribute
            childType = self.linksetAttr.type
            backName = self.linksetAttr.back

            # this is the actual linkset instance:
            theLinkSet = getattr(box.private, name)

            # cached table optimization:
            if childType in self.clerk.cache.allCached:

                # see if there's an index for this column
                sci = self.clerk.cache.index
                if (childType in sci) and backName in sci[childType]:
                    kids = sci[childType].get(box.ID)
                    if kids:
                        [theLinkSet << obj for obj in kids]

                else:

                    # no index on this column
                    for obj in self.clerk.cache.data[childType].values():
                        backLink = getattr(obj, backName)
                        if backLink is box:
                            theLinkSet << obj
            else:
                # no cache at all; hit the database.
                for obj in self.clerk.match(childType, **{self.fkey:box.ID}):
                    theLinkSet << obj




def MockClerk(dbmap=None):
    return Clerk(MockStorage(), dbmap or AutoSchema())



RamClerk = MockClerk


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


