from storage import Storage
from wherewolf import toPython
from arlo import Expr
from warnings import warn
from copy import copy

class RamStore(Storage):

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

    # (arlo.Expr, Dict) -> Bool
    def _matchRow(self, ex, row):
        # we make a copy here, or else eval()
        # will add __builtins__ to the row!
        context = copy(row)
        return bool(eval(toPython(ex), context))

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
                    if self._matchRow(where, row)]
        if orderBy is not None:
            # parse orderBy
            # break columns into a list of tuples,
            # each containing a field name and sort direction
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


    def delete(self, table, whereClause):
        self._ensuretable(table)
        rows = self._tables[table]
        if isinstance(whereClause, Expr):
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
                if self._matchRow(where, row)]

