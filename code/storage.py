"""
storage: a module for storing tabular data
"""
# * dependencies
import operator
from warnings import warn
from sets import Set
from pytypes import Date
import sqlite3 as sqlite
from arlo import Expr, Name
from wherewolf import where, toSQL

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
        res = self.match(table, where.ID==ID)
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
                                 [Name(k)==simple[k] for k in simple])
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


# old name for this class:
from ramstore import RamStore as RamStorage
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
            sql.append(" WHERE %s" % toSQL(where))
        if orderBy is not None:
            sql.append(" ORDER BY %s" % orderBy)
            # sql.append(" LIMIT 1000")
        sql = ''.join(sql)
        self._execute(sql)
        return self._dictify(self.cur)
        

    def delete(self, table, where):
        if isinstance(where, Expr):
            self._execute("DELETE FROM %s WHERE %s" % (table, toSQL(where)))
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
      

if __name__=="__main__":
    unittest.main()
    
