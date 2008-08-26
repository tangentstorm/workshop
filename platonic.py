from inspect import ismethod, isfunction, getargs

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


# same as inspect.getargspec but adds support for __call__
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


def first_match(arg, *dicts):
    for d in dicts:
        if d.has_key(arg):
            return d[arg]
    raise TypeError("missing parameter: %s" % arg)



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

        expected, defaults = signature(f)

        if expected[0]=="self":
             # @TODO: work even without convention?
             # (could check whether it's method/bound method vs function)
            expected.remove("self")

        return [first_match(arg, *list(dicts)+[defaults])
                for arg in expected]


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

