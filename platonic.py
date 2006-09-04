
import weblib
import unittest
from exceptions import Exception

class Model(dict):
    # for assertions in unit tests:
    isModel, isRedirect = True, False
    
    def __init__(self, **kwargs):
        super(Model, self).__init__()
        self.update(kwargs)

    def __getattr__(self, key):
        """
        this lets you access via . instead of []
        """
        return self[key]


class Intercept(Exception):
    def __init__(self, where, error=None, **kwargs):
         self.where = where
         self.error = error
         self.data = kwargs
         self.data["error"]=error
  
#@TODO: Redirect should subclass object, not Exception
#I'd change it now but it's still being thrown in various places
class Redirect(Exception):
    # for assertions in unit tests:
    isModel, isRedirect = False, True
    def __init__(self, where):
         self.where = where


class App(object):

    def __init__(self, default):
        # @TODO: no default actions!
        self.defaultAction = default
        self.featureSet = {}

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

    ### top-level template method:

    def dispatch(self, req, res):
        
        action = self.actionFromRequest(req) or self.defaultAction
        feature = self.buildFeature(action)

        model = self.prepareModel(req)
        try:
            result = self.invokeFeature(feature, req, res)
            if result.isModel:
                model.update(result)
            else:
                assert result.isRedirect
                raise result
        except Redirect, e:
            raise weblib.Redirect(e.where)
        except Intercept, e:
            if e.data:
                model.update(e.data)
            feature2 = self.buildFeature(e.where)
            model.update(self.invokeFeature(feature2, req,res))
            self.render(model, res, e.where)
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
