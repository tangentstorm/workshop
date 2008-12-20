from warnings import warn
import sys

# a -> Bool
def wrapped(value):
    return isinstance(value, Expr)


binaryOps = dict(
    EQ='==', NE="!=", LT="<", GT=">", LE="<=", GE=">=",
    AND='&', OR="|", XOR="^", LSHIFT="<<", RSHIFT=">>",
    ADD="+", SUB="-", MUL="*", DIV="/", MOD="%",
    POW="**", FLOORDIV='//')


unaryOps = dict(
    NEG="-", POS="+", INVERT="~")


def declare(s):
    xs = s.split()
    return "%s = %s" % (','.join(xs), ",".join('_.%s' % x for x in xs))
assert declare("a b c") == "a,b,c = _.a,_.b,_.c"


# data Expr |

class Expr(object):

    def __init__(self, left, op, right):
        self.left = left
        self.right = right
        self.op = op

    def _wrap(self, other, wrapper):
        if type(other) == tuple: return tuple(self._wrap(x,wrapper) for x in other)
        else: return other if wrapped(other) else wrapper(other)

    # (bool, str) -> Expr
    def _build(self, op, other):
        return Expr(self, op, self._wrap(other, Const))
    
    def __and__(self, other):
        return Expr(self, '&', other)

    def __or__(self, other):
        return Expr(self, '|', other)

    def __repr__(self):
        return '(%r %s %r)' % (self.left, self.op, self.right)

    def __str__(self):
        return '(%s %s %s)' % (self.left, self.op, self.right)

    def __call__(self, *others, **kw):
        if kw: warn("keyword arguments don't work yet! (%s)" % kw)
        return CallExpr(self, tuple(self._wrap(other, Const) for other in others))

    def __getattr__(self, other):
        return DotExpr(self, self._wrap(other, Name))

    def __getitem__(self, other):
        return SubExpr(self, self._wrap(other, Name))


## build the magic method combinators ################################

# Op Str , Sym str , arity -> (QueryExpr, QueryExpr -> QueryExpr)
def _makeMagic(op, sym, arity=2):
    if arity == 1:
        pass # @TODO: magic Unary operators
    else:
        def magic(self, other):
            return self._build(sym, other)
    return magic
        

for op, sym in binaryOps.items():
    magicMethod = "__%s__" % op.lower()
    if not hasattr(Expr, magicMethod):
        setattr(Expr, magicMethod, _makeMagic(op, sym, 2))



## special constructs #################################################

# | DotExpr Expr Expr
class DotExpr(Expr):
    def __init__(self, left, right):
        return super(DotExpr,self).__init__(left, '.', Name(right))
    def __repr__(self):
        return '%r.%r' % (self.left, self.right)
    def __str__(self):
        if isinstance(self.left, Arlo):
            return str(self.right)
        else:
            return '%s.%s' % (self.left, self.right)

# | CallExpr Expr Expr
class CallExpr(Expr):
    def __init__(self, left, right):
        assert type(right) == tuple, 'CallExpr wants tuple, got %s' % type(right)
        return super(CallExpr,self).__init__(left, '()', right)
    def __repr__(self):
        return '%r(%s)' % (self.left, ','.join(repr(s) for s in self.right))
    def __str__(self):
        return '%s(%s)' % (self.left, ','.join(str(s) for s in self.right))

# | SubExpr Expr Expr
class SubExpr(Expr):
    def __init__(self, left, right):
        return super(SubExpr,self).__init__(left, '[]', right)
    def __repr__(self):
        right = self.right if type(self.right) == tuple else (self.right,)
        return '%r[%r]' % (self.left, ','.join(repr(s) for s in right))
    def __str__(self):
        right = self.right if type(self.right) == tuple else (self.right,)        
        return '%s[%s]' % (self.left, ','.join(str(s) for s in right))


# Str -> Const Str
class Const(Expr):
    def __init__(self, _):
        self._ = _
    def __str__(self):
        return repr(self._)
    def __repr__(self):
        return "_(%r)" % self._


# Str -> Nameifier Str
class Name(Const):
    def __str__(self):
        return str(self._)
    def __repr__(self):
        return "%s" % self._


## builders #########################################

class Arlo(Expr):
    def __init__(self):
        pass
    def __getattr__(self, o):
        return DotExpr(self, Name(o))
    def __call__(self, o):
        return Const(o)
    def __str__(self):
        return "_"
    def __repr__(self):
        return "_"
    

_ = Arlo()

