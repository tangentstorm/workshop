from storage import *
from narrative import testcase
from warnings import warn
from handy import trim
from wherewolf import where
import unittest

class StorageTest(unittest.TestCase):

    def test_oldmatch_where(self):
        class OldMatcher(Storage):
            def _match(self, table, whereClause, orderBy):
                self.clause = whereClause
        o = OldMatcher()
        o.match("blah", ID=5)
        self.assertEquals( toSQL(o.clause), toSQL(where.ID==5))


class RamStorageTest(unittest.TestCase):

    def setUp(self):
        self.s = RamStorage()

    def test_quotes(self):
        self.s.store("test_person", name="sally o'malley")
        self.assertEquals(1, len(self.s.match("test_person",
                                              name="sally o'malley")))

    def test_store_insert(self):
        row = self.s.store("test_person", name="fred")
        self.assertEquals(row, {"ID":1, "name":"fred"})

        row = self.s.store("test_person", name="wanda")
        assert row == {"ID":2, "name":"wanda"}

        assert self.wholedb()==[{"ID":1, "name":"fred"},
                                {"ID":2, "name":"wanda"}]

# @TODO: test unicode - especially for MySQL
#     def test_unicode(self):
#         row = self.s.store("test_person", name= u"b\xe9zier")
#         self.assertEquals(row, {"ID":1,  "name":u"b\xe9zier"})
#         assert self.wholedb()==[{"ID":1, "name":u"b\xe9zier"},]

    def test_store_insertExtra(self):
        self.test_store_insert()
        self.s.store("test_person", name="rick")
        self.s.store("test_person", name="bob")
        self.s.store("test_person", name="jack")
        assert self.wholedb()==[{"ID":1, "name":"fred"},
                                {"ID":2, "name":"wanda"},
                                {"ID":3, "name":"rick"},
                                {"ID":4, "name":"bob"},
                                {"ID":5, "name":"jack"}]


    def test_oldmatch(self):
        self.test_store_insertExtra()
        match = self.s.match("test_person", where.ID==2)
        assert match[0]["name"] == "wanda", "new style broke"
        match = self.s.match("test_person", ID=2)
        assert match[0]["name"] == "wanda", "old style broke"


    def test_querybuilder_matches(self):
        self.test_store_insertExtra()
        match = self.s.match("test_person", where.ID==5 )
        assert match[0]['name'] == 'jack'

        match = self.s.match("test_person",
                            ( where.name=="fred" ) | ( where.name=="bob" ) ,
                              orderBy="name")
        self.assertEquals([u['name'] for u in match],
                          ['bob','fred'])
            

        clause = (where.ID > 1) & (where.ID <=4) | (where.name % '%ck')
        match = self.s.match("test_person", clause, orderBy='name desc')
        self.assertEquals( [u['name'] for u in match],
                           ['wanda', 'rick', 'jack', 'bob'])


    def test_querybuilder_sorting(self):
        self.test_store_insertExtra()
        self.assertEquals(['bob', 'fred', 'jack', 'rick', 'wanda'],
                          [p['name'] for p in self.s.match("test_person", orderBy='name')])

    def populate(self):
        self.test_store_insert()

    def wholedb(self):
        return self.s.match("test_person")

    def test_store_update(self):
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "frood"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"frood"},
                                  {"ID":2, "name":"wanda"}]        

    def test_store_update_longs(self):
        # same as above but with lnogs
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "frood"
        self.s.store("test_person", **row)
        self.assertEquals(self.wholedb(),
                          [{"ID":1, "name":"frood"},
                           {"ID":2, "name":"wanda"}])        

    def test_store_update_strings(self):
        # same as above but with lnogs
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "frood"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"frood"},
                                  {"ID":2, "name":"wanda"}]        

    def test_match(self):
        assert self.wholedb() == []
        self.populate()
        results = self.s.match("test_person", where.ID == 1)
        assert results == [{"ID":1, "name":"fred"}], str(results)

    def test_fetch(self):
        self.test_store_insert()
        wanda = self.s.fetch("test_person", 2)
        assert wanda["name"]=="wanda"

    def _test_delete(self, key_type):
        self.populate()
        self.s.delete("test_person", key_type(1))
        people = self.s.match("test_person")
        assert people == [{"ID":2, "name":"wanda"}]
        self.s.delete("test_person", key_type(2))
        people = self.s.match("test_person")
        assert people == []


    def test_delete_with_int_id(self):
        self._test_delete(int)

    def test_delete_with_long_id(self):
        self._test_delete(long)

    def test_delete_with_str_id(self):
        self._test_delete(str)        



class MySQLStorageTest(RamStorageTest):
    """
    To run this test, you need to create a test database
    and then define a module that connects to it. It should
    be called sqlTest.py and it should look something like this:

    # sqlTest.py
    import MySQLdb
    def connect():
        return MySQLdb.connect(
              user='test',
              passwd='whatever',
              host='localhost',
              db='test')
    """
    def setUp(self):
        dbc = sqlTest.connect()
        self.s = MySQLStorage(dbc)
        cur = dbc.cursor()
        try:
            cur.execute("DROP TABLE test_person")
        except: pass
        try:
            cur.execute(
                """
                CREATE TABLE test_person (
                    ID int not null auto_increment primary key,
                    name varchar(32)
                )
                """)
        except:
            pass

    # @TODO: test for Sets

    def test_store_quotes(self):
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "j'mo\"cha's'ha''ha"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"j'mo\"cha's'ha''ha"},
                                  {"ID":2, "name":"wanda"}]        





class PySQLiteStorageTest(RamStorageTest):

    def setUp(self):
        dbc = sqlite.connect(":memory:")
        self.s = PySQLiteStorage(dbc)
        cur = dbc.cursor()
        try:
            cur.execute("DELETE FROM test_person")
        except:
            cur.execute(
                """
                CREATE TABLE test_person (
                    ID int primary key,
                    name varchar(32)
                )
                """)

    def test_store_quotes(self):
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "j'mo\"cha's'ha''ha"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"j'mo\"cha's'ha''ha"},
                                  {"ID":2, "name":"wanda"}]        
        

if __name__ == '__main__':

    try:
        import sqlTest
    except ImportError:
        print("MySQL tests skipped.")
        print(MySQLStorageTest.__doc__)
        del MySQLStorageTest

    unittest.main()
