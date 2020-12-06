import mimetypes
import types
import re
import clerks
import strongbox
import inspect

class Model(dict):
    """
    This is a javascript-style object that aliases obj.x to obj['x']
    """
    def __init__(self, **kwargs):
        super(Model, self).__init__()
        self.update(kwargs)

    def __getattr__(self, key):
        """
        this lets you access via . instead of []
        """
        return self[key]


class Intercept(Exception):
    def __init__(self, error, *args):
        super(Intercept, self).__init__(*args)
        self.error = error
        self.data = {"error": error}


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
        assert isinstance(wrapped, types.LambdaType)
        dict.__setitem__(self, key, wrapped)

    def __getitem__(self, key):
        thunk = dict.__getitem__(self, key)
        assert callable(thunk)
        return thunk()

def getargspec(func):
    """
    :: Fun -> Tup [[Str|List] [Str] [Str]]
    TODO : :: Fun -> { args:[Str|List] var_args:[Str] key_args:[Str] }

    Get the names and default values of a function's arguments.

    A tuple of four things is returned: (args, varargs, varkw, defaults).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.
    """
    # TODO: getargspec should use inspect.getargspec (adds support for __call__)
    if inspect.ismethod(func):
        new_func = func.im_func
    elif hasattr(func, '__call__') and not inspect.isfunction(func):
        new_func = func.__call__
    else:
        new_func = func

    return inspect.getargspec(new_func)


def signature(f):
    """
    :: (expected:[Arg], defaults:[Str:Val])
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
    return Model(expected=need, defaults=defaults)


def firstMatch(arg, dicts):
    for d in dicts:
        if arg in d:
            return d[arg]
    raise TypeError("missing parameter: %s" % arg)


def callWithKeys(f, dicts):
    sig = signature(f)
    if sig.expected and sig.expected[0]=="self":
        # @TODO: work even without convention?
        # (could check whether it's method/bound method vs function)
        sig.expected.remove("self")

    search_space = list(dicts)+[sig.defaults]
    return f(*[firstMatch(arg, search_space) for arg in sig.expected])


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
        return method.upper() in self.methods

    def __repr__(self):
        return "URI({0}, {1})".format(self.path, self.methods.keys())
        

class REST(object):
    """
    RESTful mapping of (method, path) to handler objects.

    Paths are defined as regular expressions and may
    contain named groups.

    No assumptions are made concerning how the handler
    objects behave. This is merely a collection class.

    usage:

    >>> def getPerson(): pass # whatever you want
    >>> r = REST(URI('/person/(?P<name>.*)',
    ...              GET=getPerson,
    ...              PUT='put'))
    >>> r('GET','/person/fred')
    (<function getPerson at ...>, {'name': 'fred'})
    >>> r.put('/person/wanda')
    ('put', {'name': 'wanda'})

    By default, the r.meth(path) syntax converts 'meth' to
    uppercase:  r('METH', path)
    
    You can disable this by setting r.auto_up to False.
    """
    def __init__(self, *uris_):
        self.uris = uris_
        self.auto_up = True

    def __call__(self, meth, path):
        """
        return (handler, path_vars) -> (object, dict)
        """
        for uri in self.uris:
            match = uri.match(path)
            if match:
                if uri.supports(meth):
                    return uri.methods[meth], match.groupdict()
                else:
                    raise NotImplementedError('405 Method {0} Not Allowed for {1}'.format(meth, path))
            else: pass 
        else:
            # @TODO: Status 404: Not Found
            raise LookupError("404 Not Found : %s %s" % (meth, path))

    def __getattr__(self, meth):
        return lambda path:self(meth.upper() if self.auto_up else meth, path)



class AbstractApp(object):

    def buildFeature(self, req):
        raise NotImplementedError("you must override buildFeature")

    def invoke(self, req, res, feature):
        return callWithKeys(feature, self.specials(), matchdict, req)

    def render(self, req, res, feature, content):
        res.write(content)

    def onIntercept(self, intercept, feature):
        raise intercept
        
    def dispatch(self, req, res):

        feature = self.buildFeature(req)
        try:
            self.render(req, res, feature, self.invoke(req, res, feature))
        except Intercept as inter:
            self.onIntercept(req, res, feature, inter)

        # i thought about letting you chain intercepts and whatnot,
        # but for the time being that's not possible... it wouldn't
        # be hard... you'd just put that above stuff in a loop


App = AbstractApp


class Resource(object):
    pass



class BoxClerkResource(Resource):
    """
    Restful interface to a single Strongbox class in a clerk.
    """
    def __init__(self, clerk, klass):
        self.clerk = clerk
        self.klass = klass

    def match(self, *args, **kw):
        return self.clerk.match(self.klass, *args, **kw)

    def __len__(self):
        return len(self.match())

    def __getitem__(self, key):
        return clerks.BoxClerkProxy(self.clerk, self.clerk.fetch(self.klass, key))

    def __delitem__(self, key):
        return self.clerk.delete(self.klass, key)

    def __iter__(self):
        return iter(self.match())

    def __lshift__(self, instance):
        """
        stores an instance of self.klass on <<<
        """
        self.clerk.store(strongbox.asinstance(instance, self.klass))

# BEGIN
mimetypes.add_type('text/coffeescript', '.cf')


_is_wsgi_component  = 'is_wsgi_component'
_ignore_http_post   = 'ignore_http_post'

def wsgi_component(handler):
    setattr(handler, _is_wsgi_component, True)
    return handler
def is_wsgi_component(handler):
    return getattr(handler, _is_wsgi_component, False)

def ignore_http_post(handler):
    setattr(handler, _ignore_http_post, True)
    return handler
def has_ignore_post_marker(handler):
    return getattr(handler, _ignore_http_post, False)
