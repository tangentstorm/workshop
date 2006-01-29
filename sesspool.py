"""
sesspool session module
"""

import unittest
import UserDict
import weblib
import handy
import random
import string
from pickle import dumps, loads

# * Sess
# ** test
class SessTest(unittest.TestCase):
    
    def setUp(self, sid=None):
        self.builder = weblib.RequestBuilder()
        self.pool = InMemorySessPool({})
        self.sess = Sess(self.pool,
                         self.builder.build(),
                         weblib.Response())
        self.sess.start(sid)

    def test_sid(self):
        """
        A generated session id (sid) should be 32 chars.
        """
        sid = self.sess.sid
        assert len(sid)==32, "sess.sid isn't right."


    def test_persistence(self):
        """
        If you add something to one Sess object, it should persist in
        the next, provided the two Sess objects use the same SessPool.
        """
        self.sess["x"] = 10
        self.sess.stop()
        sid = self.sess.sid

        del self.sess
        self.setUp(sid)

        assert self.sess["x"]==10, "peristence doesn't work! :/"


    def test_dictstuff(self):
        
        gotError = 0
        try:
            cat = self.sess["cat"]
        except KeyError:
            gotError = 1
        assert gotError, \
               "Sess didn't raise keyError on nonexistant key"


        cat = self.sess.get("cat", "Indiana")
        assert cat == "Indiana", \
               "Sess doesn't do .get()"
        

        self.sess["cat"] = "Indy"
        assert self.sess.keys() == ['cat'], \
               "sess.keys() doesn't work"


        self.sess.clear()
        assert self.sess.get("cat") is None, \
               "sess.clear() doesn't work"


    def test_del(self):
        self.setUp("deltest")
        self.sess["cat"] = "indy"

        del self.sess["cat"]

        assert self.sess.get("cat") is None, \
               "Didn't delete key from warmData"

        self.sess["cat"] = "indy"
        self.sess.stop()
        del self.sess
        self.setUp("deltest")
        del self.sess["cat"]

        assert self.sess.get("cat") is None, \
               "Didn't delete key from coldData"


    def test_url(self):
        #@TODO: more advanced checks..
        self.sess.name = "sess"
        self.sess.sid = "ABC"
        assert self.sess.url("http://x.com") == "http://x.com?sess=ABC", \
               "sess.url() doesn't encode correctly.."

        assert self.sess.url("http://x.com?xyz=123") \
               == "http://x.com?xyz=123&sess=ABC", \
               "sess.url() doesn't encode correctly.."

        assert self.sess.url("checkout.py?auth_checkout_flag=1") \
               == "checkout.py?auth_checkout_flag=1&sess=ABC", \
               "sess.url() doesn't encode correctly.."
        

    def test_CookieSid(self):
        """
        sess should read sid from the cookie.
        """
        req = self.builder.build(cookie={"sesspool.Sess":"123"},
                             querystring="sesspool.Sess=ABC")
        sess = Sess(self.pool, req, weblib.Response())
        
        actual = sess._getSid()
        assert actual == "123", \
               "getSid doesn't read the cookie: %s.." % actual

    def test_QuerySid(self):
        """
        if no cookie, sess should read from the querystring
        """
        req = self.builder.build(querystring="sesspool.Sess=ABC")
        sess = Sess(self.pool, req, weblib.Response())

        actual = sess._getSid()
        assert actual == "ABC", \
               "getSid doesn't read the querystring (fallback): %s" % actual


    def test_newUniqueSid(self):
        """
        sids should be uniqe
        """
        self.sess.sidmaker = [2,1,1].pop # remember, pop starts at the end
        self.assertEquals(1, self.sess.newUniqueSid())

        # but if you do that when the sess exists, it should keep
        # skipping until it gets a unique one:
        self.pool.putSess("sesspool.Sess",1, "fake frozen sess data")
        self.sess.sidmaker = [2,1,1].pop # remember, pop starts at the end
        self.assertEquals(2, self.sess.newUniqueSid())

        #@TODO: while unlikely, identical sids could be generated simultaneously
        

    def tearDown(self):
        del self.sess
# ** code
"""
Sess.py : emulates PHPLIB's session support in python
"""
# NOTE: this module used to have two layers of pickling
# _warmdata and _coldData, which allowed it to store
# objects without having to import that object on every page.
# but python seems to have trouble pickling a dictionary of
# prepickled objects, so that method is deprecated.. If anyone
# really needs it, look at HotColdSess.py (the old version)
## Sess : a session handler ################

class Sess(UserDict.UserDict):
    # can't get rid of this __super until b/c UserDict is old-style class
    __super = UserDict.UserDict

    ## constructor ############################

    def __init__(self, pool, request, response):
        self.__super.__init__(self)
        self._request = request
        self._response = response
        self._pool = pool # where to store the data
        
        self.sid = ""   
        self.name = "sesspool.Sess"
        self.mode = "cookie"
        self.fallbackMode = "get"
        self.magic = "abracadabra"
        self.lifetime = 0
        self.gcTime = 1440   # purge sessions older than 24 hrs (1440 mins)
        self.gcProb = 1      # probability of garbage collection as a %

        # a function to make new sids
        self.sidmaker = handy.uid


    ## public methods ########################

    def pop(self, key):
        res = self.data[key]
        del self.data[key]
        return res

    def start(self, sid=None):
        """
        starts the session. call at the top of the page.

        Not really sure why you'd ever want to pass
        the sid variable in.. except possibly for testing..
        but PHPLIB lets you do it, so I guess I will, too.
        """
        if sid is None:
            self.sid = self._getSid()
        else:
            self.sid = sid
        #@TODO: this was an emergiceny hack. fix me!
        from Cookie import Morsel
        if isinstance(self.sid, Morsel):
            self.sid = self.sid.value
        self._thaw()        
        self._gc()


    def abandon(self):
        """
        abandons the session
        """
        self.clear()
        self.sid = ""


    def url(self, oldurl):
        """
        returns oldurl, but referencing the current session.

        If in get mode, the current session id is attached to this
        URL, else the URL is returned unmodified.
        """
        # if there's not already a querystring:
        if string.find(oldurl, "?") == -1:
            return oldurl + "?%s=%s" % (self.name, self.sid)
        else:
            return oldurl + "&%s=%s" % (self.name, self.sid)

        #@TODO: have sess.url overwrite old sess ID's in querystring


    def stop(self):
        """
        Call at end of page to stop the session. (it calls _freeze)
        """
        self._freeze()
        self._pool.done()



    ## internal methods ####################

    def newUniqueSid(self):
        sid = None        
        while sid is None:
            sid = self.sidmaker()
            if self._pool.getSess(self.name, sid):
                sid = None
        return sid

    def _getSid(self):
        """
        figures out which session id to use
        """
        sid = None

        # first try to get the sid from the browser..
        for mode in (self.mode, self.fallbackMode):
            if sid is None:
                try:
                    if mode == "cookie":
                        sid = self._request.cookie[self.name]
                    elif mode == "get":
                        sid = self._request.query[self.name]
                    else:
                        raise "Unknown mode: " + mode
                except KeyError:
                    pass

        # if that didn't work, just make one up..
        if sid is None:
            sid = self.newUniqueSid()

        #@TODO: add code for timeouts wrt setCookie
        if self.mode == "cookie":
            # always update the cookie
            self._response.addCookie(self.name, sid)
                
        return sid



    def _gc(self):
        """
        occasionally drains the sesspool
        """
        if (random.random() * 100 <= self.gcProb):
            self._pool.drain(self.name, 0)
            

    def _freeze(self):
        """
        freezes sess and dumps it into the sesspool. call at end of page
        """

        # freeze the data stuff:
        self._pool.putSess(self.name, self.sid,
                           dumps(self.data, 0)) # 1=binary, 0=ascii

    def _thaw(self):
        """
        gets a frozen sess out of the sesspool and thaws it out
        """
        frozen = self._pool.getSess(self.name, self.sid)
        if frozen is None:
            self.data = {}
        else:
            self.data = loads(frozen)
# * SessPool
# SessPool.py : classes for holding frozen Sesses :)
class SessPool:
    """
    The default SessPool uses an anydbm file.
    You should subclass this, or just build your own object with the
    same interface (getSess(), setSess(), and drain())...
    """

    #@TODO: this isn't backed up with test cases..
    
    def __init__(self, filename):
        import anydbm
        self.storage = anydbm.open(filename,"c")
        
    def getSess(self, name, sid):
        """returns the sess with the specified name and id, or None"""
        if self.storage.has_key(str(name)+str(sid)):
            return self.storage[str(name)+str(sid)]
        else:
            return None

    def putSess(self, name, sid, frozensess):
        """stores a frozen sess with the specified name and id"""
        self.storage["newkey"]="newval"
        self.storage[str(name)+str(sid)] = frozensess


    def drain(self, name, beforewhen):
        """(should) performs garbage collection to kill off old sesses"""
        # 'cept this is just a dummy version, and it don't do nuttin. :)
        pass

    def done(self):
        self.storage.close()

# * InMemorySessPool
class InMemorySessPool(SessPool):
    """
    Just uses a dictionary.
    
    **NOTE**: this WON'T WORK with, eg, mod_python unless you only
    use a single instance of apache, because the dictionary is
    local to a single python interpreter, and apache wants to have
    several...
    """
    pool = {}
    def __init__(self, dict=None):
        if dict:
            self.storage = dict
        else:
            self.storage = self.pool

    def done(self):
        pass

# * SqlSessPool
class SqlSessPool:
    """
    This uses a DB-API 2.0 compliant Connection object to store Sessions.
    It expects a table like:

    CREATE TABLE web_sess (
        name varchar(32),
        sid varchar(64),
        sess blob,
        tsUpdate bigint,
        primary key (name, sid)
    );


    (tsUpdate is a bigint instead of a timestamp because
     sqlite doesn't do timestamps...)
    """

    def __init__(self, dbc, table='web_sess'):
        self.dbc = dbc
        self.table = table


    def getSess(self, name, sid):
        cur = self.dbc.cursor()
        cur.execute("select sess from " + self.table + \
                    " where name='" + name + "' and sid='" + sid + "'")

        try:
            ## GRR.. the win32 mysql has a problem with this..
            #@TODO: find a way to isolate stuff like this..
            row = cur.fetchone()
        except:
            row = None
            
        if row is None:
            return row
        else:
            return row[0]


    def putSess(self, name, sid, frozensess):
        import string, time       
	frozen = string.replace(frozensess, "'", "''")
        cur = self.dbc.cursor()
        sql =\
            """
            REPLACE INTO %s (sess, name, sid, tsUpdate)
            VALUES ('%s', '%s', '%s', %s)
            """ % (self.table, frozen, name, sid, time.time())
        try:
            cur.execute(sql)
        except Exception, e:
            raise Exception, "error storing session: %s \n SQL WAS:\n %s" \
                  % (e, sql)
        self.dbc.commit()
    

    def drain(self, name, beforeWhen):
        cur = self.dbc.cursor()
        #@TODO: cleanup beforeWhen (garbage collection)
        sql =\
            """
            DELETE FROM %s WHERE name='%s' and tsUpdate < '%s'
            """ % (self.table, name, `beforeWhen`)
        cur.execute(sql)

    def done(self):
        pass
# * --
if __name__=="__main__":
    unittest.main()
