"""
storage: a module for storing tabular data
"""
# * dependencies
import unittest
import operator
import warnings
from pytypes import Date

# * optinal dependencies
try: import sqlite
except ImportError: sqlite = None

try:
    import MySQLdb
except ImportError:
    MySQLdb = None


# * QueryExpression
class QueryExpression(object):
    OPS = {
        "&"         : "AND",
        "|"         : "OR",
        "startswith": "LIKE",
        "endswith"  : "LIKE",
    }
    
    def __init__(self, left, right, operation):
        self.left = left
        self.right = right
        self.operation = operation
        #@TODO: remove this!
        self.pattern = (left, right, operation)

    
    def __and__(self, other):
        return QueryExpression(self, other, '&')

    def __or__(self, other):
        return QueryExpression(self, other, '|')

    def __str__(self):
        format = isinstance(self.right, QueryExpression) and '(%s %s %s)' or "(%s %s '%s')" 
        right = self.operation == "startswith" and "%s%%" % self.right or self.right
        right = self.operation == "endswith" and "%%%s" % right or right
        op = self.OPS.get(self.operation, self.operation)
        return format % (self.left, op, str(right))
# * QueryBuilder
# ** test
class QueryBuilderTest(unittest.TestCase):


    def test_simple(self):
        clause = where('a') < 5
        assert str(clause) == "(a < '5')", clause

    def test_complex(self): 
        a = where("a") == 1
        b = where("b") == 2
        #import pdb; pdb.set_trace()
        clause = a | b
        self.assertEquals(str(clause), "((a = '1') OR (b = '2'))")

    def test_like(self):
        clause = where("name").startswith("a")
        self.assertEquals(str(clause), "(name LIKE 'a%')")
# ** code
class QueryBuilder(object):

    def __init__(self, name=''):
        self._name = name

    def __eq__(self, other):
        return QueryExpression(self._name, other, '=') 

    def __ne__(self, other):
        return QueryExpression(self._name, other, '!=') 

    def __lt__(self, other):
        return QueryExpression(self._name, other, '<') 
    
    def __gt__(self, other):
        return QueryExpression(self._name, other, '>')

    def __ge__(self, other):
        return QueryExpression(self._name, other, '>=')
    
    def __le__(self, other):
        return QueryExpression(self._name, other, '<=')

    def startswith(self, other):
        return QueryExpression(self._name, other, 'startswith') 

    def endswith(self, other):
        return QueryExpression(self._name, other, 'endswith') 

    def __str__(self):
        return self._name
# * where
where = QueryBuilder
# * Storage
# ** test
class StorageTest(unittest.TestCase):

    def test_oldmatch(self):
        class OldMatcher(Storage):
            def _match(self, table, whereClause, orderBy):
                self.clause = whereClause
        o = OldMatcher()
        o.match("blah", ID=5)
        self.assertEquals( str(o.clause), "(ID = '5')")
# ** code
class Storage(object):

    def store(self, table, **row):
        if row.get("ID"):
            return self._update(table, **row)
        else:
            return self._insert(table, **row)

    def fetch(self, table, ID):
        res = self.match(table, where("ID")==ID)
        if len(res)!=1:
            raise LookupError, "match(%r, ID=%r) returned %i rows." \
                  % (table, ID, len(res))
        return res[0]
    ## abstract:

    def delete(self, table, ID):
        raise NotImplementedError
        
    def match(self, table, whereClause=None, orderBy=None, **simple):      
        assert not (whereClause and simple), \
               "where/simple queries are mutually exclusive"
        if simple:
            whereClause = reduce(operator.and_,
                                 [where(k)==simple[k] for k in simple])
        return self._match(table, whereClause, orderBy)

    def _match(self, table, where, orderBy=None):          
        raise NotImplementedError
    
    def _insert(self, table, **row):
        raise NotImplementedError

    def _update(self, table, **row):
        raise NotImplementedError
# * MockStorage
# ** test
class MockStorageTest(unittest.TestCase):

    def setUp(self):
        self.s = MockStorage()

    def test_store_insert(self):
        row = self.s.store("test_person", name="fred")
        assert row == {"ID":1, "name":"fred"}

        row = self.s.store("test_person", name="wanda")
        assert row == {"ID":2, "name":"wanda"}

        assert self.wholedb()==[{"ID":1, "name":"fred"},
                                {"ID":2, "name":"wanda"}]

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
        match = self.s.match("test_person", where("ID")==2)
        assert match[0]["name"] == "wanda", "new style broke"
        match = self.s.match("test_person", ID=2)
        assert match[0]["name"] == "wanda", "old style broke"


    def test_querybuilder_matches(self):
        self.test_store_insertExtra()
        match = self.s.match("test_person", where("ID")==5 )
        assert match[0]['name'] == 'jack'

        match = self.s.match("test_person", ( ( where("name")=="fred" )
                                         |  ( where("name")=="bob" ) ), "name")
        self.assertEquals([u['name'] for u in match],
                          ['bob','fred'])
            
        
        
        match = self.s.match("test_person", ((where("ID") > 1)
                                             &(where("ID") <= 4))
                                           |(where("name").endswith('ck')),
                                         'name desc')
        self.assertEquals( [u['name'] for u in match],
                           ['wanda', 'rick', 'jack', 'bob'] )



    def test_querybuilder_sorting(self):
        self.test_store_insertExtra()
        assert [p['name'] for p in self.s.match("test_person", orderBy='name')] == ['bob', 'fred', 'jack', 'rick', 'wanda']

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
        row = self.s.fetch("test_person", 1L)
        row["name"] = "frood"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"frood"},
                                  {"ID":2, "name":"wanda"}]        

    def test_store_update_strings(self):
        # same as above but with lnogs
        self.populate()
        row = self.s.fetch("test_person", "1")
        row["name"] = "frood"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"frood"},
                                  {"ID":2, "name":"wanda"}]        

    def test_match(self):
        assert self.wholedb() == []
        self.populate()
        results = self.s.match("test_person", where("ID") == 1)
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
# ** code
class MockStorage(Storage):
    OPS = {
        "="   : "__eq__",
        ">"   : "__gt__",
        "<"   : "__lt__",
        ">="  : "__ge__",
        "<="  : "__le__",
        "!="  : "__ne__",
        "&" : "__and__",
        "|"  : "__or__",
    }

    def __init__(self):
        self._tables = {}
        self._counter = {}

    def _ensuretable(self, name):
        if not name in self._tables:
            self._tables[name]=[]
            self._counter[name]=0

    def _nextid(self, table):
        self._counter[table] += 1
        return self._counter[table]

    def _dictmatch(self, expression, subject):
        # RICK: uses querybuilder to match instead.
        (prop, val, op) = expression.pattern
        if op in ["|","&"]:
            return getattr(self._dictmatch(expression.left, subject), self.OPS[expression.operation])(self._dictmatch(expression.right, subject))
        else:
           
            # get the property value to check
            # take the value after the right-most period
            # Omitted due to the new QueryBuilder object
            #if '.' in prop: prop = prop[prop.rindex('.')+1:]
            p = subject[prop]
            # perform the operation from the pattern against the value
            try:
                op = self.OPS.get(op,op)
                res = getattr(str(p).lower(), op)(str(val).lower())
                # str.index returns 0 if a match is found in the first character, so return 1
                if op == 'index': return 1
                return res
            except ValueError:
                # str.index raises ValueError if no match is found, return 0
                return 0

    def store(self, table, **row):
        self._ensuretable(table)
        return Storage.store(self, table, **row)

    def _update(self, table, **row):
        rec = self.fetch(table, row["ID"])
        rec.update(row)
        return rec

    def _insert(self, table, **row):
        rec = {}
        rec.update(row)
        rec["ID"] = self._nextid(table)
        self._tables[table].append(rec)
        return rec

    def _match(self, table, where=None, orderBy=None):
        self._ensuretable(table)
        if where is None:
            rows = self._tables[table]
        else:
            rows = [row for row
                    in self._tables[table]
                    if self._dictmatch(where, row)]
        if orderBy is not None:
            # parse orderBy
            # break columns into a list of tuples, containing field name and sort direction
            setcol = lambda x: x.lower().endswith(' desc') and (x.split()[0], 'desc') or (x.strip(), 'asc')
            cols = [setcol(c) for c in orderBy.split(',')]

            # invert() takes n and returns its opposite (invert(15) == -15)
            # rcmp() is a reverse of the cmp() function
            invert = lambda x: x-2*x
            rcmp = lambda x, y: invert(cmp(x, y))

            def listsort(x, y):
                """
                for each column, do a cmp() or rcmp()
                if the columns are equal, move to the next to sort
                if all columns are equal then return 0
                """
                for c in cols:
                    i = c[1]=='asc' and cmp(x[c[0]], y[c[0]]) or rcmp(x[c[0]], y[c[0]])
                    if i: return i
                return i
            rows.sort(listsort)
        return rows

    def fetch(self, table, ID):
        res = self.match(table, where("ID") == ID)
        if len(res)!=1:
            raise LookupError, "match(%r, ID=%r) returned %i rows." \
                  % (table, ID, len(res))
        return res[0]

    def delete(self, table, w):
        self._ensuretable(table)
        rows = self._tables[table]
        if isinstance(w, QueryBuilder):
            # repeat until no rows are deleted
            l = 1
            while l > 0:
                l = len(self.__deleteMatch(w, rows))
        else:
            for i in range(len(rows)):
                if rows[i]["ID"]==long(w):
                    rows.remove(rows[i])
                    break

    def __deleteMatch(self, where, rows):
        # the loop stops once a row is deleted
        return [rows.remove(row) for row
                in rows
                if self._dictmatch(where, row)]

    
# * MySQLStorage
# ** test
class MySQLStorageTest(unittest.TestCase):
    """
    To run this test, you need to create a test database
    and then define a module that connects to it. It should
    be called sqlTest.py and it should look something like this:

    # sqlTest.py
    import MySQLdb
    dbc = MySQLdb.connect(
              user='test',
              passwd='whatever',
              host='localhost',
              db='test')
    """
    def setUp(self):
        try:
            import sqlTest
            self.skip = False
        except ImportError:
            warnings.warn("skipping MySQL tests: no sqlTest module")
            self.skip = True
            return
        self.s = MySQLStorage(sqlTest.dbc)
        cur = sqlTest.dbc.cursor()
        try:
            cur.execute("DELETE FROM test_person")
        except:
            cur.execute(
                """
                CREATE TABLE test_person (
                    ID int not null auto_increment primary key,
                    name varchar(32)
                )
                """)


    def test_store_quotes(self):
        if self.skip : return
        self.populate()
        row = self.s.fetch("test_person", 1)
        row["name"] = "j'mo\"cha's'ha''ha"
        self.s.store("test_person", **row)
        assert self.wholedb() == [{"ID":1, "name":"j'mo\"cha's'ha''ha"},
                                  {"ID":2, "name":"wanda"}]        
        

    # other test are inherited from MockStorage...
# ** code
class MySQLStorage(Storage):
    #qb = SQLQueryBuilder
    #q = SQLQueryBuilder()

    def __init__(self, dbc):
        self.dbc = dbc
        self.cur = dbc.cursor()


    def _dictify(self, cur):
        """
        converts cursor.fetchall() results into a list of dicts
        """
        res = []
        for row in cur.fetchall():
            d = {}
            for i in range(len(cur.description)):
                d[cur.description[i][0]] = row[i]
            res.append(d)
        return res


    def _toSQLString(self, val):
        """
        Turns a value into a quoted string suitable for MySQL
        """
        if isinstance(val, Date) and str(val)=='0-0-0':                
            return "NULL"
        elif val is None:
            return "NULL"
        else:
            return "'" + "''".join(str(val).split("'")) + "'"
            

    def _insert_main(self, table, **row):
        # generate column/value lists for INSERT
        cols = ', '.join(row.keys())
        vals = ', '.join([self._toSQLString(v) for v in row.values()])

        sql = "INSERT INTO %s (%s) VALUES (%s)" % (table, cols, vals)
        self._execute(sql)

        return self._getInsertID()

    def _insert(self, table, **row):
        id = self._insert_main(table, **row)
        return self.fetch(table, id)

    def _getInsertID(self):
        # new way:
        if hasattr(self.cur, "insert_id"):
            return self.cur.insert_id()
        elif hasattr(self.cur, "_insert_id"):
            return self.cur._insert_id
        else:
            raise Exception("insert_id not found!") 


    def _update(self, table, **row):

        sql = "UPDATE " + table + " SET"
        for col,val in row.iteritems():
            sql += " " + col + "=" + self._toSQLString(val) + ","
        sql = sql[:-1]

        # whoops! thanks to Andy Todd for this line:
        sql += " WHERE ID = %d" % row["ID"]

        self._execute(sql)
        return self.fetch(table, row["ID"])
        

    def _match(self, table, where=None, orderBy=None):
        sql = ["SELECT * FROM %s" % table]
        if where is not None:
            sql.append(" WHERE %s" % str(where))
        if orderBy is not None:
            sql.append(" ORDER BY %s" % orderBy)
        sql = ''.join(sql)
        self._execute(sql)
        return self._dictify(self.cur)
        

    def delete(self, table, where):
        if isinstance(where, QueryBuilder):
            self._execute("DELETE FROM %s WHERE %s" % (table, str(where)))
        else:
            # might be a string, int, or long
            self._execute("DELETE FROM %s WHERE ID=%s" % (table, where))


    def _execute(self, sql):
        self.maxAttempts = 3
        attempt = 0
        if MySQLdb:
            theException = MySQLdb.OperationalError
        else:
            theException = NotImplementedError # hack!
            
        while attempt < self.maxAttempts:
            try:
                self.cur.execute(sql)
                break
            except theException, e:
                # OperationalError: usually means the db is down.
                attempt += 1
                if attempt >= self.maxAttempts:
                    raise Exception("couldn't connect after %s tries: %s"
                                    % (attempt, e))
                if attempt >= self.maxAttempts:
                    raise 
            except Exception, e:
                raise Exception, str(e) + ":" + sql

            
# * PySQLiteStorage
# ** test

class PySQLiteStorageTest(MockStorageTest):

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
        

    # other test are inherited from MockStorage...
# ** code
class PySQLiteStorage(MySQLStorage):

    def _getInsertID(self):
        return self.cur.lastrowid
    def _execute(self, sql):
        super(PySQLiteStorage, self)._execute(sql)
        #self.cur.con.commit()

    def _insert_main(self, table, **row):
        id = super(PySQLiteStorage, self)._insert_main(table, **row)
        self._execute("UPDATE %s SET ID=%s where ID IS NULL"
                      % (table, id))
        return id
      
# * --
if __name__=="__main__":
    unittest.main()
    
