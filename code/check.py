"""
Provides checks similar to unittest.assertXXX,
but can be run outside of a TestCase.
"""
import difflib

_unwrap = lambda x : x() if callable(x) else x

def _assert(cond, err, msg):
    """
    Bit -> Err -> ( Str or Lam -> Str )

    The lambda option allows you to pass in code that
    only gets evaluated if the assertion fails.
    """
    if cond: pass
    else: raise err(_unwrap(msg))

def type(obj, typ, msg=None):
    """
    :: a -> * -> Str -> Either TypeError a

    ensures the object has the specified type (using isinstance)
    """
    _assert(isinstance(obj, typ),
        TypeError, msg or ("expected type: %s, found: %r" % (typ, obj)))
    return obj

def is_in(obj, group, msg=None):
    """
    ensures membership in a collection
    """
    _assert(obj in group, LookupError, msg or
        "%s was not found in %s" % (obj, group))

def not_in(obj, group, msg=None):
    """
    guards against membership in a collection
    """
    _assert(obj not in group, LookupError, msg or
                                           "%s should not have been in %s" % (obj, group))


def same_text(a, b, msg=None):
    _assert(a == b, AssertionError, msg or (lambda :
        "\n".join(difflib.ndiff(a.split("\n"),b.split("\n")))))


def equal(a, b, msg=None):
    _assert(a == b, ValueError, msg or "check.equal failure: %r !=  %r" % (a, b))
