import arlo
from arlo import Expr, DotExpr, CallExpr, Name, Const, transform
from warnings import warn
from copy import deepcopy


class WhereExpr(arlo.StartExpr):
    def __call__(self, o):
        warn("where(field) should be where.x now!!!")
        return DotExpr(self, Name(o))


where = WhereExpr()

OPS = {
    '|': 'OR',
    '&': 'AND',
    '^': 'XOR',
    '==': '=',
    '%': 'LIKE'}

_sqlDispatch = {
    Expr: lambda f, a, o, b: '(%s %s %s)' % (f(a), OPS.get(o, o), f(b)),
    DotExpr: (lambda f, a, b:
              f(b) if a.__class__ in (arlo.StartExpr, WhereExpr)
              else '%s.%s' % (f(a), f(b))),
    CallExpr: lambda f, a, b: '%s(%s)' % (f(a), f(b)),
    #   SubExpr ?
    Name: lambda f, a: str(a),
    Const: (lambda f, a:
            (repr(a).replace('L', '') if type(a) == int else
             ("'%s'" % a.replace("'", "''")) if type(a) == str else
             repr(a)))}


def pyLike(f, a, b):
    pat = b.op
    if isinstance(b, arlo.Const) and isinstance(pat, str):
        if pat.endswith('%'): return '%s.startswith(%r)' % (f(a), pat[:-1])
        if pat.startswith('%'): return '%s.endswith(%r)' % (f(a), pat[1:])
        return "re.match(%s, %s)" % (f(b), f(a))
    else:
        # not a string, so assume it's a real mod operator
        return '(%s %% %s)' % (f(a), f(b))


# the only difference between python and sql expressions (for now)
# are the operators used
_pyDispatch = deepcopy(_sqlDispatch)
_pyDispatch[Expr] = lambda f, a, o, b: pyLike(f, a, b) if o == '%' else '(%s %s %s)' % (f(a), o, f(b))
_pyDispatch[Const] = lambda f, a: repr(a)


# Expr -> str
def toSQL(ex):
    """
    generate sql from an arlo Expr
    (only does where clause for now)
    """
    return transform(toSQL, _sqlDispatch, ex)


sql = toSQL


def toPython(ex):
    return transform(toPython, _pyDispatch, ex)
