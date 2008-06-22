
import weblib
import unittest
from exceptions import Exception

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
 

class DictWrap:
    """
    missing values default to '0'
    use case: checkbox values from a form going into
    the redirect expression. eg: ?bool=%(bool)s
    if bool is unchecked, then nothing gets passed in,
    so a normal dict would raise a keyerror. instead,
    this just returns a '0'...

    Ideally, the default would be '' or it would be
    parsed from the __expected__ parameter, but
    @TODO: the code that handles __expected__ is gone!

    However, since this is currently only used for
    checkboxes, it does the job...
    """
    def __init__(self, d):
        self.d = d
    def __getitem__(self, key):
        return self.d.get(key, '0')


class App(object):

    def __init__(self, default=None):
        # @TODO: no default actions!
        self.defaultAction = default
        self.featureSet = {}
        self.bounceTo = {} # where to go after intercept
        self.success = {} # or after success

    ### default implemenations:
        
    def actionFromRequest(self, req):
        return req.get("action","").replace(" ","_")
        
    def getRawFeature(self, action):
        assert action in self.featureSet, "unknown action: %s" % action
        return self.featureSet[action]

    def initFeature(self, f, action):
        return f()

    def prepareModel(self, req):
        return {}

    def buildFeature(self, action):
        raw_feature = self.getRawFeature(action)
        return self.initFeature(raw_feature, action)

    def invokeFeature(self, f, req, res):
        #@TODO: signature dispatch
        return f.handle(req,res)

    def render(self, m, res, action):
        # this ignores action but cornerops uses action 
        # to pick the correct tile. eventually there
        # shouldn't be any output at all except
        # possibly on Intercepts
        res.write(str(m))

    def onSuccess(self, action, where):
        self.success[action] = where
        
    def onIntercept(self, action, bounceTo):
        self.bounceTo[action] = bounceTo
        
    def whereToGoWhenIntercepted(self, action):
        return self.bounceTo.get(action)

    ### top-level template method:    

    def dispatch(self, req, res):
        
        action = self.actionFromRequest(req) or self.defaultAction
        feature = self.buildFeature(action)

        model = self.prepareModel(req)
        try:
            result = self.invokeFeature(feature, req, res)
            if result is None:
                raise weblib.Redirect(self.success[action] % DictWrap(req))
            elif isinstance(result,dict) or isinstance(result, Model):
                model.update(result)
            else:
                raise TypeError, \
                      "result should be none or Model, not %s" % result
        except Intercept, e:
            bounceTo = self.whereToGoWhenIntercepted(action)
            model.update(e.data) # for {:error:}
            feature2 = self.buildFeature(bounceTo)
            model.update(self.invokeFeature(feature2, req,res))
            self.render(model, res, bounceTo)
        else:
            self.render(model, res, action)

        # i thought about letting you chain intercepts and whatnot,
        # but for the time being that's not possible... it wouldn't
        # be hard... you'd just put that above stuff in a loop


class AppTest(unittest.TestCase):

    def test_chooseAction(self):
        def result_for(req):
            return App(default="the_default").chooseAction(req)
        assert result_for({}) == "the_default"
        assert result_for({"action":"do this"}) == "do_this"

if __name__=="__main__":
    unittest.main()
