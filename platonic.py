
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

