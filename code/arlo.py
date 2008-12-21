"""
Arlo : Algebraic Reified Language Objects ?? :)

Arlo is a generic combinator library for python.

usage:

>>> from arlo import _
>>> ex = _.f(_(1) + 1) == _.g( 1 + 1 )
>>> type(ex)
<class 'arlo.Expr'>
>>> ex.op
'=='

Names preceded by  _. or constants enclosed in _()
are converted into objects that are automatically
composed into objects:

>>> ex
(_.f((_(1) + _(1))) == _.g(_(2)))


Notice how "_(1) + 1" inside f() becomes "_(1) + _(1)"
but the "1 + 1" inside g() is evaluated immediately and
then preserved as "_(2)".

These expression objects can be converted back to python
source code and evaluated at any time:

>>> ex = ( _.x >= 10 )
>>> py = str( ex )
>>> x = 5
>>> eval(str(ex))
False
>>> x = 50
>>> eval(str(ex))
True


While str(ex) converts the expression to normal python
source code, repr(ex) converts it to 'reified' or 'lazy'
source, so you can run it now or save it for later.

>>> str(ex)
'(x >= 10)'
>>> repr(ex)
'(_.x >= _(10))'


Each expression object has three members: left, right, and op:

>>> ex = ( _.x + 1 )
>>> ex.left
_.x
>>> ex.right
_(1)
>>> ex.op
'+'

You can write code to inspect and modify these members
just as with any other python object. The only thing
thing special about Expr objects is that they happen to
remember which symbols were used to create them.


You can declare large numbers of reified identifiers
with: exec arlo.declare(names), where names is just
a string full of identifiers separated by spaces.

>>> arlo.declare('a b c')
'a,b,c = _.a,_.b,_.c'
>>> exec arlo.declare('a b c')
>>> a, b, c
(_.a, _.b, _.c)


Expression objects can be combined using any of the
following binay operators:

  == != < > <= >=  & | ^ << >>  + - * / % ** //


The unary prefix operators ('not', '-', '+', and '~')
have not been implemented.

You can use the dot ( . ) to chain together anything
that would be a valid python identifier:

>>> _.this  .Is  .all  .one   .expression 
_.this.Is.all.one.expression


Note the capitalization on the word 'Is'.
You have to be careful about reserved words!

>>> _.this .is .not
  File "<stdin>", line 1
    _.this .is .not
             ^
SyntaxError: invalid syntax


Arlo makes no attempt to process the meaning of your
expressions, so you're free to put them inside lists,
tuples, dictionaries, or even lambdas.

You're also free to mix and match reified and unreified
code. Remember that pretty much anything but spaces and
dots start a new subexpression, so if you don't start the
sub-expression with _ , python will evaluate it immediately.

  arlo     ->    python
  --------------------------
  _.a      ->    eval('a')
  _.a.b    ->    eval('a.b')
  _(1)     ->    eval('1')
  _.a[b]   ->    eval('a')[b]
  _.a[_.b] ->    eval('a[b]')
  _.a(b)   ->    eval('a')(b)
  _.a(_.b) ->    eval('a')(_.b)

  

Even with these restrictions, it's possible to create very
complex mini-languages with these combinators. For example,
here's an expression that tries to look like a definition
of quicksort in haskell:


exec arlo.declare('sig let Ord a where y xs y p')
qsort = [
    sig. qsort == Ord.a >> [a] >> [a] ,
    let. qsort (  []     ) == [] ,
    let. qsort ( _[p:xs] ) == ( _.qsort.lesser + [p] + _.qsort.greater ,
                              where (
                                  _.lesser  == [ y | y << xs , y < p  ],
                                  _.greater == [ y | y << xs , y >= p ])) ]



Of course, it doesn't actually compute quicksort by itself.
As far as python is concerned, all this code does is define
some variables and then use them to calculate a list (named 'qsort')
containing three expression objects. 

All arlo does is build interesting data structures that remember the
symbols used to create them. It's up to *you* to tell python what to
do with the data structure once you have it.

"""
from warnings import warn
import sys

# a -> Bool
def wrapped(value):
    return isinstance(value, Expr)

# see http://docs.python.org/library/operator.html
biOps = dict(
    EQ='==', NE="!=", LT="<", GT=">", LE="<=", GE=">=",
    AND='&', OR="|", XOR="^", LSHIFT="<<", RSHIFT=">>",
    ADD="+", SUB="-", MUL="*", DIV="/", MOD="%",
    POW="**", FLOORDIV='//')


unOps = dict(
    NEG="-", POS="+", INVERT="~")


def declare(s):
    xs = s.split()
    return "%s = %s" % (','.join(xs), ",".join('_.%s' % x for x in xs))


# data Expr = Expr left:Expr op:BiOp  right:Expr
#           | DotExpr  left:Expr right:Expr
#           | CallExpr left:Expr right:Expr
#           | SubExpr Expr Expr
#           | Name n:String
#           | Const o:Object
#
# @TODO: slices, unary operators

class Expr(object):

    def __init__(self, left, op, right):
        self.left = left
        self.right = right
        self.op = op
        self.arity = 3

    def _pattern(self, slots=None):
        arity = self.arity if slots is None else slots
        if arity == 0: return ()
        if arity == 1: return (self.op, )
        if arity == 2: return (self.left, self.right)
        if arity == 3: return (self.left, self.op, self.right)

    def _wrap(self, other, wrapper):
        if type(other) == tuple: return tuple(self._wrap(x,wrapper) for x in other)
        else: return other if wrapped(other) else wrapper(other)

    # (bool, str) -> Expr
    def _build(self, op, other):
        return Expr(self, op, self._wrap(other, Const))
    
    def __repr__(self):
        return '(%r %s %r)' % (self.left, self.op, self.right)

    def __str__(self):
        return '(%s %s %s)' % (self.left, self.op, self.right)

    def __unicode__(self):
        return unicode(str(self))

    def __call__(self, *others, **kw):
        if kw: warn("keyword arguments don't work yet! (%s)" % kw)
        return CallExpr(self, tuple(self._wrap(other, Const) for other in others))

    def __getattr__(self, other):
        return DotExpr(self, self._wrap(other, Name))

    def __getitem__(self, other):
        return SubExpr(self, self._wrap(other, Name))

##     def __contains__(self, other):
##         '''
##         note operators are reversed
##         '''
##         return Expr(self._wrap(other, Const), 'in', self)


## build the magic method combinators ################################

# Op Str , Sym str , arity -> (QueryExpr, QueryExpr -> QueryExpr)
def _makeMagic(op, sym, arity=2):
    if arity == 1:
        pass # @TODO: magic Unary operators
    else:
        def magic(self, other):
            return self._build(sym, other)
    return magic
        

for op, sym in biOps.items():
    magicMethod = "__%s__" % op.lower()
    if not hasattr(Expr, magicMethod):
        setattr(Expr, magicMethod, _makeMagic(op, sym, 2))



## suffix constructs #################################################

# abstract
class SuffixExpr(Expr):
    _symbol = ' '
    def __init__(self, left, right):
        super(SuffixExpr,self).__init__(left, self._symbol, self._wrap(right, Name))
        self.arity = 2

# | DotExpr Expr Expr
class DotExpr(SuffixExpr):
    _symbol = '.'
    def __repr__(self):
        return '%r.%r' % (self.left, self.right)
    def __str__(self):
        if isinstance(self.left, StartExpr):
            return str(self.right)
        else:
            return '%s.%s' % (self.left, self.right)

# | CallExpr Expr Expr
class CallExpr(SuffixExpr):
    _symbol = '()'
    def __repr__(self):
        return '%r(%s)' % (self.left, ','.join(repr(s) for s in self.right))
    def __str__(self):
        return '%s(%s)' % (self.left, ','.join(str(s) for s in self.right))

# | SubExpr Expr Expr
class SubExpr(SuffixExpr):
    _symbol = '[]'
    def __repr__(self):
        right = self.right if type(self.right) == tuple else (self.right,)
        return '%r[%r]' % (self.left, ','.join(repr(s) for s in right))
    def __str__(self):
        right = self.right if type(self.right) == tuple else (self.right,)        
        return '%s[%s]' % (self.left, ','.join(str(s) for s in right))


# abstract
class LeafExpr(Expr):
    def __init__(self, x):
        self.op = x
        self.arity = 1

# Str -> Const object
class Const(LeafExpr):
    def __str__(self):
        return repr(self.op)
    def __repr__(self):
        return "_(%r)" % self.op


# Str -> Nameifier Str
class Name(LeafExpr):
    def __str__(self):
        return str(self.op)
    def __repr__(self):
        return "%s" % self.op


## builders #########################################

class StartExpr(Expr):
    def __init__(self):
        self.arity = 0
    def __getattr__(self, o):
        return DotExpr(self, Name(o))
    def __call__(self, o):
        return Const(o)
    def __str__(self):
        return "_"
    def __repr__(self):
        return "_"


_ = ARLO = StartExpr()

def pattern(ex):
    """
    Returns the arguments passed to the constructor,
    for haskell-style pattern matching.

    In other words, the following line should always
    return a copy of any Expr ex:

    ex.__class__(*pattern(ex))
    """
    return ex._pattern()


def transform(f, dispatch, ex):
    """
    uses a family of functions to traverse the
    expression and eventually 
    
    by passing in the top level entry point (f)
    we can create groups of functions that can
    inherit from each other.

    for example, pyDispatch is just like sqlDispatch
    except for one rule, but if we hard-coded the 'f'
    we'd have to maintain two copies of each rule
    """
    return dispatch[ex.__class__](f, *pattern(ex))

