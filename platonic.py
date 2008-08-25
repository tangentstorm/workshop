import inspect

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


def signature(callable):
    """
    returns a list of arguments and a dict of default values
    """
    spec = inspect.getargspec(callable)
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

        return [first_match(arg, *dicts)
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

