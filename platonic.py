import warnings
from types import LambdaType
import re

class Model(dict):
    
    def __init__(self, **kwargs):
        super(Model, self).__init__()
        self.update(kwargs)

    def __getattr__(self, key):
        """
        this lets you access via . instead of []
        """
        return self[key]


class Intercept(Exception):
    def __init__(self, error):
         self.error = error
         self.data = {"error":error}



class lazydict(dict):
    """
    A lazy loading dictionary. All values
    must be wrapped with (lambda : value)

    >>> data = dict(x=5)
    >>> lazy = lazydict( x = lambda: data['x']*2)
    >>> lazy['x']
    10
    >>> data['x']=100
    >>> lazy['x']
    200
    >>> lazy['y'] = lambda: lazy['x'] +1
    >>> lazy['y']
    201
    >>> data['x']=12
    >>> lazy['x']
    24
    >>> lazy['y']
    25
    
    """

    def __setitem__(self, key, wrapped):
        assert isinstance(wrapped, LambdaType)
        dict.__setitem__(self, key, wrapped)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)()
         


# same as inspect.getargspec but adds support for __call__
from inspect import ismethod, isfunction, getargs
def getargspec(func):
    """Get the names and default values of a function's arguments.

    A tuple of four things is returned: (args, varargs, varkw, defaults).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.
    """
    if ismethod(func):
        func = func.im_func
    
    if not isfunction(func):
        if hasattr(func, '__call__'):
            return getargspec(func.__call__)
        else:
            raise TypeError('%r is not a Python function' % func)
        
    args, varargs, varkw = getargs(func.func_code)
    return args, varargs, varkw, func.func_defaults


def signature(f):
    """
    returns a list of arguments and a dict of default values
    """
    spec = getargspec(f)
    need = spec[0]
    vals = spec[3]
    defaults = {}
    if vals:
        for k,v in zip(need[-len(vals):], vals):
            # this is important for fastCGI/etc:
            # (because default values are evaluated only once)
            assert type(v)!=list, "default lists are mutable! use tuples!"
            defaults[k]=v
    return need, defaults


def firstMatch(arg, *dicts):
    for d in dicts:
        if d.has_key(arg):
            return d[arg]
    raise TypeError("missing parameter: %s" % arg)


def callWithKeys(f, *dicts):
    expected, defaults = signature(f)

    if expected[0]=="self":
        # @TODO: work even without convention?
        # (could check whether it's method/bound method vs function)
        expected.remove("self")
        
    return f(*[firstMatch(arg, *list(dicts)+[defaults])
               for arg in expected])


class URI(object):
    def __init__(self, path, **methodHandlers):
        self.path = path
        self.re = re.compile(path)
        
        self.methods = {}
        for k,v in methodHandlers.items():
            self.methods[k.upper()] = v

    def match(self, path):
        return self.re.match(path)

    def supports(self, method):
        return (method.upper() in self.methods)
        

class REST(object):
    """
    RESTful mapping of (method, path) to handler objects.

    Paths are defined as regular expressions and may
    contain named groups.

    No assumptions are made concerning how the handler
    objects behave. This is merely a collection class.

    usage:

    >>> def getPerson(): pass # whatever you wante
    >>> r = REST(URI('/person/(?P<name>.*)',
    ...              GET=getPerson,
    ...              PUT='put'))
    >>> r('GET','/person/fred')
    (<function getPerson at ...>, {'name': 'fred'})
    >>> r.put('/person/wanda')
    ('put', {'name': 'wanda'})

    By default, the r.meth(path) syntax converts 'meth' to
    uppercase:  r('METH', path)
    
    You can disable this by setting r.autoup to False.
    """
    def __init__(self, *uris):
        self.uris = uris
        self.autoup = True

    def __call__(self, meth, path):
        """
        return (handler, pathvars) -> (object, dict)
        """
        for uri in self.uris:
            match = uri.match(path)
            if match:
                if uri.supports(meth):
                    return (uri.methods[meth], match.groupdict())
                else:
                    raise NotImplementedError('405 Method Not Allowed')
            else: pass 
        else:
            # @TODO: Status 404: Not Found
            raise LookupError("404 Not Found : %s %s" % (meth, path))

    def __getattr__(self, meth):
        return lambda(path):\
               self(meth.upper() if self.autoup else meth, path)



class AbstractApp(object):

    def buildFeature(self, req):
        raise NotImplementedError("you must override buildFeature")

    def invoke(self, req, res, feature):
        # @TODO: signature-based dispatch
        return feature().handle(req, res)

    def render(self, req, res, feature, content):
        res.write(content)

    def onIntercept(self, intercept, feature):
        raise intercept


    def buildArgs(self, f, *dicts):
        warnings.warn("use platonic.callWithKeys", DeprecationWarning)
        return callWithKeys(f, *dicts)
        
    def dispatch(self, req, res):

        feature = self.buildFeature(req)
        try:
            self.render(req, res, feature, self.invoke(req, res, feature))
        except Intercept, inter:
            self.onIntercept(req, res, feature, inter)

        # i thought about letting you chain intercepts and whatnot,
        # but for the time being that's not possible... it wouldn't
        # be hard... you'd just put that above stuff in a loop


App = AbstractApp

