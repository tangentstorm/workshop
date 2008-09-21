"""
storage: a module for storing tabular data
"""
# * dependencies
import operator
import warnings
from sets import Set
from pytypes import Date
import sqlite3 as sqlite
from arlo import QueryBuilder, where

# optional depedencies
try: import sqlite3 as sqlite
except ImportError: sqlite = None

try: import MySQLdb
except ImportError: MySQLdb = None


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

    # @TODO: this came unchanged from Clerk. Can Clerk subclass Storage??
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


    def _match(self, table, where, orderBy=None):          
        raise NotImplementedError
    
    def _insert(self, table, **row):
        raise NotImplementedError

    def _update(self, table, **row):
        raise NotImplementedError



class RamStorage(Storage):
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

        (prop, val, op) = expression.pattern
        if op in ["|","&"]:
            return getattr(self._dictmatch(expression.left, subject), self.OPS[expression.operation])(self._dictmatch(expression.right, subject))
        else:
           
            # get the property value to check
            # take the value after the right-most period
            # Omitted due to the new QueryBuilder object (arlo.where)
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
            setcol = lambda x: ((x.split()[0], 'desc') if x.lower().endswith(' desc')
                                else (x.strip(), 'asc'))
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

    def delete(self, table, whereClause):
        self._ensuretable(table)
        rows = self._tables[table]
        if isinstance(whereClause, QueryBuilder):
            # repeat until no rows are deleted
            l = 1
            while l > 0:
                l = len(self.__deleteMatch(whereClause, rows))
        else:
            for i in range(len(rows)):
                if rows[i]["ID"]==long(whereClause):
                    rows.remove(rows[i])
                    break

    def __deleteMatch(self, where, rows):
        # the loop stops once a row is deleted
        return [rows.remove(row) for row
                in rows
                if self._dictmatch(where, row)]



# old name for this class:
MockStorage = RamStorage

    
class MySQLStorage(Storage):

    def __init__(self, dbc):
        self.dbc = dbc
        self.cur = dbc.cursor()


    def _dictify(self, cur):
        """
        converts cursor.fetchall() results into a list of dicts
        also removes Set() for enums.
        """
        res = []
        for row in cur.fetchall():
            d = {}
            for i in range(len(cur.description)):
                d[cur.description[i][0]] = (
                    row[i].pop() if isinstance(row[i], Set) else row[i] )
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
            return "'" + "''".join(unicode(val).split("'")) + "'"
            

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
        if hasattr(self.cur, "lastrowid"):
            return self.cur.lastrowid
        elif hasattr(self.cur, "insert_id"):
            return self.cur.insert_id()
        elif hasattr(self.cur, "_insert_id"):
            return self.cur._insert_id
        elif hasattr(self.cur, "lastrowid"):
            return self.cur.lastrowid
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
            sql.append(" WHERE %s" % unicode(where))
        if orderBy is not None:
            sql.append(" ORDER BY %s" % orderBy)
#        sql.append(" LIMIT 1000")
        sql = ''.join(sql)
        self._execute(sql)
        return self._dictify(self.cur)
        

    def delete(self, table, where):
        if isinstance(where, QueryBuilder):
            self._execute("DELETE FROM %s WHERE %s" % (table, unicode(where)))
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
                #print sql
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

            

    # other test are inherited from RamStorage...
# ** code
class PySQLiteStorage(MySQLStorage):

    def _getInsertID(self):
        return self.cur.lastrowid
    def _execute(self, sql):
        super(PySQLiteStorage, self)._execute(sql)
        self.dbc.commit()

    def _insert_main(self, table, **row):
        id = super(PySQLiteStorage, self)._insert_main(table, **row)
        self._execute("UPDATE %s SET ID=%s where ID IS NULL"
                      % (table, id))
        return id
      
# * --
if __name__=="__main__":
    unittest.main()
    
