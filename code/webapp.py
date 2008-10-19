from platonic import lazydict, callWithKeys
from weblib import RequestData, Redirect
from genshi.template import TemplateLoader
import os, traceback
import wsgiref.handlers
import traceback
import sys
import cgi

class FileHandler(object):
    def __init__(self, path):
        self.path = path

    def __call__(self, env, start):
        start('200 OK', [])
        yield open(path[1:]).read()


def fileHandlerFactory(meth, path):
    """
    Serve static content.
    """
    if ((meth == "GET")
        and (not os.path.sep in path[1:])
        and os.path.exists(path[1:])):
        return StaticFile(path), {}
    else:
        raise LookupError


class WebApp(object):
    """
    Base class for platonic web apps.
    """
    def __init__(self, baseURL, handlerFactories):
        self.factories = handlerFactories 

    def specials(self, env):
        """
        per-request special objects
        """
        return lazydict (
            _env       = (lambda: env),
        )

    def findHandler(self, meth, path):
        """
        returns a handler and dictionary of params from the path
        """
        print self.factories
        for factory in self.factories:
            try:
                print ("%s factory(%s, %s) ->" % (factory, meth, path)),
                res = factory(meth, path)
                print "   ", res
                return res
            except LookupError:
                print "    not found"
                pass
        #raise LookupError("%s %s" % (meth, path))



    def __call__(self, env, start):
        try:
            gen = self.theme.render200(start,env["PATH_INFO"], 
                                       self.getModel(env))
            
        except LookupError:
            gen = self.theme.render404(start, env["PATH_INFO"])

        except Redirect, e:
            gen = self.theme.render303(start, location=str(e))

        except Exception, e:
            gen = self.theme.render500(start, str(e), traceback.format_exc())

        for each in gen:
            yield each


    def contentArgs(self, env):
        """
        returns form data as a dict. if form data is not urlencoded,
        it returns a lazydict with one key: _content , which maps
        to whatever was in the body of the request.
        """
        _content = (lambda: env['wsgi.input'].read(
                                int(env.get("CONTENT_LENGTH", 0))))

        if ((env["REQUEST_METHOD"]=="POST") and 
            (env.get("CONTENT_TYPE",'')=='application/x-www-form-urlencoded')):
            return RequestData(_content())
        else:
            # @TODO: multipart/form-data
            return lazydict(_content = _content)


    def getModel(self, env):

        # parse content first, as it may override the method (POST tunneling)
        contentArgs = self.contentArgs(env)

        meth = env['REQUEST_METHOD']
        if (meth == "POST") and '@method' in form:
            meth = contentArgs["@method"]

        # now select the handler based on the method and path:
        handler, pathArgs = self.findHandler(meth, env['PATH_INFO'])
        
        specialArgs = self.specials(env)
        queryArgs = RequestData(env["QUERY_STRING"])

        allArgs = [specialArgs, pathArgs, queryArgs, contentArgs]

        return callWithKeys(handler, *allArgs)



class GenshiTheme(object):
    """
    A web app that uses genshi templates.    
    """
    def __init__(self, baseURL, theme="default"):
        self.baseURL = baseURL

    def render200(self, start, path, model):
        start('200 OK', [('content-type', 'application/xhtml+xml')])

        template = None
        if not template:
            yield str(model)

        elif template.endswith(".gen"):
            model.setdefault("base", self.baseURL)
            yield (TemplateLoader(THEME, variable_lookup='lenient')
                   .load(template)
                   .generate(**model)
                   .render()
                   .encode('utf-8'))


    def render303(self, start, location):
        start('303 Redirect', [('Location', location)])
        yield ''

    def render404(self, start, path):
        start('404 Not Found', [])
        yield '404 Not Found: %s' % path

    def render500(self, start, err, trace):
        start('500 Internal Server Error', [])
        yield '500 Internal Server Error\n'
        yield err
        yield trace
        



## WSGI Error Handler ############################

class CGITracebackHandler(wsgiref.handlers.CGIHandler):
    def handle_error(self):
        tb = html_error("".join(traceback.format_exception(
            sys.exc_type, sys.exc_value, sys.exc_traceback)))
        if not self.headers_sent:
            self.start_response("500 Internal Server Error",
                           [("Content-type", "text/html")])
        self.result = "\n".join([html_head("error"),
                                 tb, html_foot()])
        self.finish_response()

## HTML headers ##################################

def html_head(title):
    return (
        '''
        <html>
        <head>
        <title>%s</title>
        <style type="text/css">
        body {
          font-family: verdana, arial, san-serif;
          font-size: 10pt; }
        h1 { color: green; }
        .error {
           color: gold;
           background: #993333;
           border: solid red 5px;
           white-space: pre; }
        </style>
        </head>
        <body>
        <h1>%s</h1>
        ''' % (title, title))

def html_error(msg):
    return '<div class="error">%s</div>' % cgi.escape(str(msg))


def html_foot():
    return (
        '''
        </body>
        </html>
        ''')

## helpers #######################################

def dict_from_fieldstorage(fs):
    query_dict = {}
    for key in fs.keys():
        query_dict[key] = fs.getvalue(key)
    return query_dict


def my_url(environ):
    # look up this script's own url
    return "http://%s%s" % (environ["HTTP_HOST"],
                            environ["REQUEST_URI"])


## WSGI Runners ##################################
def runCGI(f):
    CGITracebackHandler().run(f)

