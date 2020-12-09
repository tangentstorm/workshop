"""
weblib: Classes for easy server-side web scripting in Python.
"""
__ver__="$Id: __init__.py,v 1.30 2003/08/24 10:19:05 sabren Exp $"

# * imports
import sys, io
import urllib.parse
from handy import trim
import traceback
import os, sys
import handy
from http.cookies import SimpleCookie, Morsel
import weblib
import random
import os
import unittest
import tempfile
from handy import trim
try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
from handy import trim, sendmail


# * Reponse codes
# ** Redirect
class Redirect(Exception):
    """
    Raise this when you want to redirect but don't have access to
    a response object. (Eg, for testing without the RES variable,
    or just so you don't have to keep passing it down a call stack)
    """
    pass
# ** Finished
class Finished(Exception):
    """
    Raise this when you're done with your page.
    Or call RES.end()
    """
    pass
# * escaping text
# ** htmlEncode:
def htmlEncode(s):
    """
    htmlEncode(s) ->  s with >, <, and & escaped as &gt;, &lt; and &amp;
    """
    res = ""
    for ch in s:
        if ch == ">":
            res = res + "&gt;"
        elif ch=="<":
            res = res + "&lt;"
        elif ch=="&":
            res=res + "&amp;"
        else:
            res = res + ch
    return res

# ** urlEncode

def urlEncode(what):
    """This works the way ASP's urlEncode does, OR lets you do it
    the urllib way (using a dict)"""
    
    res = None
    import urllib
    if isinstance(what, str):
        res = urllib.parse.quote(what)
    elif isinstance(what, dict):
        res = urllib.parse.urlencode(what)
    else:
        raise TypeError("urlEncode doesn't know how to deal with this kind of data")

    return res
    
# ** urlDecode

def urlDecode(what):
    if isinstance(what, str):
        return urllib.parse.unquote(what.replace("+", " "))
    # elif isinstance(what, dict):   # -- this makes no sense.
    #     res = urllib.parse.urldecode(what)
    else:
        raise TypeError("urlDecode doesn't know how to deal with this kind of data")


# * stuff that should be in handy
def tuplify(thing):
    return thing if isinstance(thing, tuple) else (thing, )

def _tupleMerge(head, tail):
    return tuplify(head)+tuplify(tail)


# * Engine
# ** test
class EngineTest(unittest.TestCase):

    def setUp(self):
        self.builder = RequestBuilder()

    def test_globals(self):
        myscript = trim(
            """
            import weblib
            assert REQ.__class__.__name__ == 'Request', 'req'
            assert RES.__class__.__name__ == 'Response', 'res'
            assert ENG.__class__.__name__ == 'Engine', 'eng'
            """)
        eng = Engine(script=myscript)
        eng.run()
        assert eng.error is None, eng.error
        self.assertEquals(Engine.SUCCESS, eng.result)
        

    def test_print(self):
        eng = Engine(script=trim(
            """
            import weblib
            print >> RES, 'this should show'
            print 'this should not'
            """))
        tempout, sys.stdout = sys.stdout, io.StringIO()
        eng.run()
        sys.stdout, tempout = tempout, sys.stdout
        assert eng.response.buffer == "this should show\n", \
               "doesn't grab prints after import weblib!"
        assert tempout.getvalue() == "this should not\n", \
               "doesn't print rest to stdout"


    def test_exit(self):
        """
        @TODO: why or why not trap sys.exit() ?

        Really, you just shouldn't call sys.exit().

        I was trapping it for a while, but it no longer
        works... Who cares, though? Instead, raise Finished
        or call RES.end()
        """
        try:
            eng = Engine(script="raise SystemExit")
            eng.run()
            gotError = 0
        except SystemExit:
            gotError = 1
        assert gotError, "Engine should not trap sys.exit()."


    def test_runtwice(self):
        eng = Engine(script='print >> RES, "hello"')
        eng.run()
        try:
            eng.run()
            gotError = 0 
        except:
            gotError = 1
        assert gotError, "you should not be able to use engine twice!"

    def test_on_exit(self):
        """
        engine.do_on_exit(XXX) should remember XXX and call it at end of page.
        """
        def nothing():
            pass
        
        eng = Engine(script="")
        assert len(eng._exitstuff)==0, \
               "exitstuff not empty by default"
        
        eng.do_on_exit(nothing)
        assert len(eng._exitstuff)==1, \
               "do_on_exit doesn't add to exitstuff" 

        eng._exitstuff = []
        
        eng = Engine(script=trim(
            """
            # underscores on next line are just for emacs.. (trim strips them)
        ___ def cleanup():   
                print >> RES, 'wokka wokka wokka'
            ENG.do_on_exit(cleanup)
            """))
        eng.execute(eng.script)
        assert len(eng._exitstuff) == 1, \
               "didn't register exit function: %s" % str(eng._exitstuff)
        eng._exit()
        assert eng.response.buffer=='wokka wokka wokka\n', \
               "got wrong response: %s" % eng.response.buffer
        


    def test_result(self):
        eng = Engine(script='1+1')
        assert eng.result == None, \
               "engine.result doesn't default to None"

        eng.run()
        assert eng.result == eng.SUCCESS, \
               "engine.result doesn't return SUCCESS on success"

        eng = Engine(script="print 'cat' + 5")
        eng.run()
        assert eng.result == eng.EXCEPTION, \
               "engine.result doesn't return EXCEPTION on error."

        eng = Engine("assert 1==0, 'math is working.. :('")
        eng.run()
        assert eng.result == eng.FAILURE, \
               "engine.result doesn't return FAILURE on assertion failure."

        eng = Engine("import weblib; raise weblib.Redirect, 'url?query'")
        eng.run()
        assert eng.result == eng.REDIRECT, \
               "engine.result doesn't return REDIRECT on redirect."

    ## CGI-SPECIFIC (needs to move) ############################

    ## @TODO: this is really a test of Request
    def test_request(self):
        os.environ["QUERY_STRING"]="enginetest"

        engine = Engine(script="")
        assert engine.request.query.string=="enginetest", \
               "engine has wrong default request"
        del engine

        req = self.builder.build(querystring="e=mc2&this=a+test")
        engine = Engine("pass", request=req)
        assert engine.request.query.string=="e=mc2&this=a+test", \
               "engine has wrong passed-in request:" + \
               engine.request.query.string

    #@TODO: move to testRequest
    def test_form(self):
        weblib.MYFORM = {"a":"bcd"}
        try:
            myscript = trim(
                """
                import weblib
                assert REQ.form is weblib.MYFORM, \
                    'request uses wrong form'
                """)
            req = self.builder.build(form=weblib.MYFORM)
            eng = weblib.Engine(request=req, script=myscript)
            eng.run()
            assert eng.result == eng.SUCCESS, eng.result
        finally:
            del weblib.MYFORM

    def test_hadProblem(self):
        e = Engine(script="x = 1"); e.run()
        assert not e.hadProblem()
        e = Engine(script="raise hell"); e.run()
        assert e.hadProblem()
        e = Engine(script="assert 0"); e.run()
        assert e.hadProblem()


    def test__main__(self):
        e = Engine(script=trim(
            """
            if __name__=='__main__':
               print >> RES, 'sup?'
            """))
        e.run()
        assert e.response.buffer =="sup?\n"
        
            

    # @TODO: revisit test_pathInfo
    # ----------------------------
    # engine needs to set pathinfo so that response
    # can redirect to ?lsakdfjlsdkafj
    # scripts should not pull it out of os.environ
    # because that won't work for twisted
    # instead, the engine for each service should
    # do this. (twisted, cgi, etc...)
    
    # this is what was in pathinfo.app:
    # print >> RES, "this is just a dummy script used by testEngine.py"
    
    #def test_pathInfo(self):
    #    eng = Engine(script=open("spec/pathinfo.app"))
    #    assert eng.request.pathInfo == "spec/pathinfo.app", \
    #           "Engine doesn't set .pathInfo correctly for open()ed scripts."

    # I commented this test out because it relies on an external
    # file and that's no fun.


    def test_redirectToQuerystring(self):
        eng = Engine("import weblib; raise weblib.Redirect('?x=1')",
                     request=RequestBuilder().build(path="test.app"))
        eng.run()
        assert ('Location', 'test.app?x=1') in eng.response.headers

    
# ** code

class Engine(object):

    SUCCESS   = "* success *"
    FAILURE   = "* failure *"
    EXCEPTION = "* exception *"
    REDIRECT  = "* redirect *"
    EXIT      = "* exit *"

    def __init__(self, script=None,  request=None, path="."):
        """
        script should be a string with actual code.
        """
        self.script = script
        self.request = request or weblib.RequestBuilder().build()
        self.response = self.makeResponse()

        self.result = None
        self.error = None
        self.path = path
        self.makeGlobals()
        
        # stuff to do at exit:
        self._exitstuff = []
        self.setPathInfo()

    def makeGlobals(self):
        self.globals = {}
        self.globals['__name__']='__main__'
        self.globals['SITE_NAME']= None
        self.globals['SITE_MAIL']= None
        self.globals["ENG"] = self
        self.globals["REQ"] = self.request
        self.globals["RES"] = self.response

    def setPathInfo(self):
        """
        This (technology/app server specific) routine sets the
        PATH_INFO CGI variable.
        """
        #@TODO: should this really be PATH_INFO? how about SCRIPT_NAME?
        if not getattr(self.request, "pathInfo", None):
            if (type(self.script) == type("")):
                self.request.pathInfo = "UNKNOWN_SCRIPT.py"
            else:
                self.request.pathInfo = self.script.name


    def makeResponse(self):
        return weblib.Response()
    

    def do_on_exit(self, func, *targs, **kargs):
        """
        Register a callback for the end of page.
        """
        self._exitstuff.append((func, targs, kargs))

    def _exit(self):
        """
        run exit stuff.. based on python 2.0's atexit._run_exitfuncs()
        """
        while self._exitstuff:
            func, targs, kargs = self._exitstuff[-1]
            func(*targs, **kargs)
            self._exitstuff.remove(self._exitstuff[-1])

    def _exec(self, script):
        """
        This is in its own method so a subclass can restrict execution.
        """
        exec(script, self.globals)

    def execute(self, script):
        """
        Call this to execute a chunk of code.
        """
        self.result = self.SUCCESS
        try:
            self.setPathInfo() 
            self._exec(script)
        except weblib.Finished:
            self.result = self.EXIT
        except AssertionError as e:
            self.result = self.FAILURE
            self.error = e
        except weblib.Redirect as e:
            self.result = self.REDIRECT
            try:
                where = str(e)
                if where[0]=="?":
                    # redirect to querystring goes to current page:
                    where = self.request.path + where
                self.response.redirect(where)
            except weblib.Finished:
                pass
        except Exception as e:
            self.result = self.EXCEPTION
            self.exception = e
            self.error = "".join(traceback.format_exception(
                sys.exc_type,
                sys.exc_value,
                sys.exc_traceback))

    def chdir(self):
        os.chdir(self.path)

    def runDotWeblibPy(self):
        path = self.path + os.sep + ".weblib.py"
        if os.path.exists(path):
            # we use execute instead of run because we only want
            # to run the setup once.
            self.execute(open(path))

    def runScript(self):
        # self.result is None if nothing's been run yet
        # it would be error or exception if dotWeblibPy had a problem
        if (self.result is None) or (self.result == self.SUCCESS):
            self.execute(self.script)
        else:
            # treat as normal error, assertion failure, or SystemExit
            pass 

    def run(self):
        assert not self.result, "can't use an Engine more than once"
        self.chdir()
        self.runDotWeblibPy()
        self.runScript()
        self._exit()

    def hadProblem(self):
        assert self.result
        return self.result in (Engine.FAILURE, Engine.EXCEPTION)
# * RequestData
# ** test
class RequestDataTest(unittest.TestCase):

    def test_basics(self):
        s = "a=1&b=2&b=3&e=em+cee+squared"
        q = RequestData(s)
        assert q.string == s
        assert q["a"] == "1", \
               "simple querystring not working"
        assert q["b"] == ("2", "3"), \
               "doesn't tupleize multiple values"
        assert q["e"] == "em cee squared", \
               "query's urldecoding not working"


# ** code

class RequestData(dict):
    """
    a dict-like object to represent form contents or a query string
    """
    def __init__(self, s: str):
        super().__init__()
        self.type = "application/x-www-form-urlencoded"
        try:
            self.string = s.decode('utf-8') if isinstance(s, bytes) else s
        except UnicodeDecodeError:
            raise
        for k, v in self._split_pairs(self.string).items():
            self[k] = v

    @staticmethod
    def _split_pairs(what, splitter="&", decode=1):
        res = {}
        for pair in what.split(splitter):
            if decode:
                pair = urlDecode(pair)
            s = pair.split("=", 1)
            k = s[0]
            if len(s) > 1:
                v = s[1]
            else:
                v = ''
            res[k] = _tupleMerge(res[k], v) if k in res else v
        return res

# * RequestBuilder
iso = "ISO-8859-1"
import urllib

class RequestBuilder(object):
    """
    should only be used for CGI and testing
    """
    def build(self, method=None, host=None, path=None, querystring=None,
              form=None, cookie=None, content=None, remoteAddress=None):
        if content and not method: method = "POST"
        return Request(
            method= method or os.environ.get("REQUEST_METHOD", "GET"),
            host = host or os.environ.get("SERVER_NAME"),
            path = path or os.environ.get("PATH_INFO"),
            query=RequestData(querystring or
                              urllib.parse.unquote(os.environ.get("QUERY_STRING",'')).decode(iso).encode("utf8")
                              ),
            form=form,
            cookie=SimpleCookie(cookie or os.environ.get("HTTP_COOKIE", "")),
            content=content or self.fetchContent(),
            remoteAddress = remoteAddress or "unknownhost")
    def fetchContent(self):
        return sys.stdin.read(int(os.environ.get("CONTENT_LENGTH",0) or 0))
# * Request
# ** test
class RequestTest(unittest.TestCase):

    def setUp(self):
        self.builder = RequestBuilder()

    def test_getitem(self):
        req = self.builder.build(querystring="a=1&aa=2&aa=3&z1=querystring",
                      form={"b":"2", "z1":"form", "z2":"form"},
                      cookie={"c":"3", "z1":"cookie", "z2":"cookie",
                              "z3":"cookie"})
       
        assert req["a"] == "1", \
               "getitem scews up on querystring"
        assert req["aa"] == ("2", "3"), \
               "getitem screws up on multiple values"
        assert req["b"] == "2", \
               "getitem screws up on forms"
        assert req["c"] == "3", \
               "getitem screws up on cookies"

        # it should fetch things in this order:
        assert req["z1"][0] == "querystring", \
               "getitem goes in wrong order (z1)"
        assert req["z2"][0] == "form", \
               "getitem goes in wrong order (z2)"
        assert req["z3"] == "cookie", \
               "getitem goes in wrong order (z3)"

    def test_keys(self):
        req = self.builder.build(querystring="querystring=1",
                      form={"form":"1"},
                      cookie={"cookie":"1"})
        keys = req.keys()
        keys.sort()
        
        assert keys== ['cookie','form','querystring'], \
               "request.keys() doesn't work."


    def test_get(self):
        req = self.builder.build(querystring="a=1")
        assert req.get("a") == "1", \
               "get breaks for valid keys"
        assert req.get("b") is None, \
               "get breaks for non-present keys"


    def test_encoding(self):
        req = self.builder.build(content="a=<>")
        assert req.form["a"] == "<>", \
               "doesn't handle <> correctly (got %s)" \
               % repr(req.form["a"])


    def test_content(self):
        req = self.builder.build()
        assert req.content =="", \
               "request.content doesnt default to blank string"
        
        req = self.builder.build(content="abcdefg")
        assert req.content == "abcdefg", \
               "request doesn't store content correctly."
      

    def NOT_IMPLEMENTED_test_multipart(self):
        #@TODO: RE-ENABLE THIS!!!!!!!!!!!
        return 
        req = self.builder.build(
            method="POST",
            contentType=
            "multipart/form-data; boundary=---------------------------7d035c305e4",
            content=weblib.trim(
            """
            -----------------------------7d035c305e4
            Content-Disposition: form-data; name="upfile"; filename="mime.test"
            Content-Type: text/plain

            THIS IS A TEST
            THIS IS ONLY A TEST

            -----------------------------7d035c305e4
            Content-Disposition: form-data; name="action"
            
            upload
            -----------------------------7d035c305e4
            Content-Disposition: form-data; name="twovalues"
            
            value1
            -----------------------------7d035c305e4
            Content-Disposition: form-data; name="twovalues"
            
            value2
            -----------------------------7d035c305e4--
            """            
            ))

        #@TODO: try MIME-generation module instead of hard-coding the string..
        assert request.form.get("action")=="upload", \
               weblib.trim(
               """
               form values don't work on multipart forms. (got %s)
               -----------
               ** NOTE **
               this test works when I test manually, but not via
               the test script.. The bug appears to be in using StringIO
               (rather than sys.stdin) with the cgi.FieldStorage, or in
               some invisible characters in the MIME stuff.. 
               I have never been able to track it down... (help?)
               -----------
               """
               % repr(request.form.get("action")))

        assert request.form["upfile"].filename == "C:\mimetest.txt", \
               "file uploads don't return FieldStorage objects"

        assert request.form["twovalues"] == ("value1", "value2"), \
               "multi-value fields break on multi-part forms."


    def test_ampersand(self):
        """
        ampersand is %26 .. what if the querystring or
        form or whatever has an ampersand in it? At one
        point, urlDecode()ing it would break the value in
        two pieces...
        """
        ampstr = "a=apple&b=boys%26girls"
        req = self.builder.build(content=ampstr, querystring=ampstr)
        goal = {"a":"apple", "b":"boys&girls"}

        assert req.query == goal, \
               ".query doesn't grok ampersands."

        assert req.form == goal, \
               ".form doesn't grok ampersands."

# ** code
class Request(object):
    """
    A read-only dictionary that represents an HTTP reqeust
    """
    def __init__(self, method, host, path, query, form,
                 cookie, content, remoteAddress):
        self.method = method
        self.host = host
        self.path = path
        self.query = query
        self.cookie = cookie
        self.form = form or RequestData(content or "")
        self.content = getattr(self.form, "string", "")
        self.remoteAddress = remoteAddress
        
    def __getitem__(self, key):
        res = None
        for dict in [self.query, self.form, self.cookie]:
            if dict.has_key(key):
                if res is None:
                    res = dict[key]
                else:
                    res = _tupleMerge(res, dict[key])
        if res is None:
            raise KeyError(key)
        return res

    def get(self, key, failobj=None):
        try:
            return self[key]
        except KeyError:
            return failobj

    def keys(self):
        res = {}
        for dict in [self.query, self.form, self.cookie]:
            for key in dict.keys():
                res[key] = 1
        return res.keys()

    def has_key(self, key):
        for dict in [self.query, self.form, self.cookie]:
            if dict.has_key(key):
                return 1
        return 0
# * Response
# ** test

    def setUp(self):
        self.response = Response()
        
    def test_init(self):
        assert self.response.buffer=="", \
               "response.buffer doesn't initialize correctly."

    def test_write(self):
        self.response.write("hello, world")
        assert self.response.buffer == "hello, world", \
               "response.write() doesn't work"
        
    def test_end(self):
        try:
            self.response.end()
            gotIt = 0
        except Finished:
            gotIt = 1
        assert gotIt, "response.end() doesn't raise Finished!"

    def test_simpleRedirect(self):
        #@TODO: use idxDict for status
        self.assertRaises(Finished,
                          self.response.redirect, "http://www.sabren.com/")
        assert self.response.headers[0] == ("Status", "303 Redirect"),\
               "didn't get Status: 303 header on redirect- %s" \
               % self.response.headers
        assert self.response.headers[1] \
               == ("Location", "http://www.sabren.com/"),\
               "didn't get Location: header on redirect - %s" \
               % self.response.headers

    def test_queryRedirect(self):
        """
        if the first char of a redirect is ?, should redirect to
        the current url with the querystring.

        BUT: this is actually handled by Engine, because Response
        doesn't know anything at all about what page we're looking
        at. That info is stored in the Request.

        See EngineTest.test_redirectToQuerystring() for details.       
        """       
        self.assertRaises(Finished, self.response.redirect, "?a=b")
# ** code
class Response(object):
    """
    Minimal HTTP Response object
    """
    def __init__(self, out=None):
        self.out = out
        self.contentType = "text/html"
        self.headers = []
        self.buffer = ""
        self._sentHeaders = 0        

    def write(self, data):
        self.buffer = self.buffer + data
    
    def flush(self):
        if self.out:
            if not self._sentHeaders:
                self.out.write(self.getHeaders())
                self._sentHeaders = 1
            self.out.write(self.buffer)
            self.buffer = ""
            
    def end(self):
        self.flush()
        raise Finished

    ## header stuff #####################################
        
    def getHeaders(self):
        res = "Content-type: " + self.contentType + "; charset=utf-8\n"
        for k,v in self.headers:
            res += "%s:%s\n" % (k,v)
        return res + "\n"

    def addHeader(self, key, value):
        assert value is not None
        self.headers.append((key, value))

    def addCookie(self, key, value):
        # @TODO: this was an emergecny hack. fix me!
        if isinstance(value, Morsel):
            self.addHeader("Set-Cookie", key + "=" + value.coded_value)
        else:
            self.addHeader("Set-Cookie", key + "=" + value)

    def redirect(self, url):
        self.addHeader("Status", "303 Redirect")
        self.addHeader("Location", url)
        self.end()
# * OutputDecorator
# ** test
class OutputDecoratorTest(unittest.TestCase):

    def wrap(self, code):
        eng = Engine(script=code)
        eng.run()
        out = OutputDecorator(eng)
        return out
        
    def test_normal(self):
        out = self.wrap("print >> RES, 'hello, world!'")
        self.assertEquals(out.getHeaders(), 'Content-type: text/html; charset=utf-8\n\n')
        self.assertEquals(out.getBody(), 'hello, world!\n')

    def test_assert(self):
        out = self.wrap("assert 0, 'the assertion failed'")
        self.assertEquals(out.getHeaders(), trim(
            '''
            Status: 500 Internal Server Error
            Content-Type: text/html; charset=utf-8
            
            '''))
        assert out.getBody().count('the assertion failed'), out.getBody()

    def test_except(self):
        out = self.wrap("raise hell")
        self.assertEquals(out.getHeaders(), trim(
            '''
            Status: 500 Internal Server Error
            Content-Type: text/html; charset=utf-8

            ''')) 
        assert out.getBody().count('NameError'), out.getBody()
        
# ** code
class OutputDecorator(object):

    def __init__(self, eng):
        self.eng = eng
        
    def getHeaders(self):
        if self.eng.hadProblem():
            return self.errHeaders()
        else:
            return self.eng.response.getHeaders()

    def getBody(self):
        if self.eng.hadProblem():
            res = self.errStart()
            if self.eng.result == Engine.FAILURE:
                res += u"<b>assertion failure:</b>"
                #res += str(self.eng.error)
                res +=  self.errTraceback()
            elif self.eng.result == Engine.EXCEPTION:
                res +=  self.errTraceback()
            res += self.errFooter()
            return res.decode("utf8")
        else:
            return self.eng.response.buffer

    #@TODO: consolidate html and plain text error reports?
    def sendError(self):
        SITE_MAIL = self.eng.globals["SITE_MAIL"]
        SITE_NAME = self.eng.globals["SITE_NAME"]
        assert SITE_MAIL is not None, "must define SITE_MAIL first!"
        hr = "-" * 50 + "\n"
        msg = trim(
            """
            To: %s
            From: cgi <%s>
            Subject: uncaught exception in %s

            """ % (SITE_MAIL, SITE_MAIL, SITE_NAME))
        msg += "uncaught exception in %s\n\n" % self.eng.request.pathInfo
        msg += hr
        msg += str(self.eng.error)
        msg += hr
        msg += "FORM: %s\n"  % self.eng.request.form
        msg += "QUERYSTRING: %s\n" % self.eng.request.query.string
        msg += "COOKIE: %s\n" % self.eng.request.cookie

        if hasattr(self, "sess"):
            msg = msg + "SESSION DATA:\n"
            for item in self.eng.sess.keys():
                msg += item + ': '
                try:
                    msg += self.eng.sess[item] + "\n"
                except:
                    msg += "(can't unpickle)\n"
        else:
            msg += "NO SESSION DATA\n"
        msg += hr
        msg += "OUTPUT:\n\n"
        msg += self.eng.response.getHeaders() + "\n"
        msg += self.eng.response.buffer + "\n"
        msg += hr

        msg.encode("utf-8")

        sendmail(msg)

    def errTraceback(self):
        res = '<h1>uncaught exception while running %s</h1>\n'\
              % self.eng.request.pathInfo
        res+= '<pre class="traceback">\n' \
              + htmlEncode(self.eng.error) + "</pre>\n"
        res+= "<b>script input:</b>\n"
        res+= '<ul>\n'
        res+= '<li>form: %s</li>\n' % self.eng.request.form
        res+= '<li>querystring: %s</li>\n' % self.eng.request.query.string
        res+= '<li>cookie: %s</li>\n' % self.eng.request.cookie
        res+= '</ul>\n'
        if self.eng.globals.has_key("SESS"):
            res+= '<h2>session data:</h2>\n'
            res+= '<ul>\n'
            for item in self.eng.globals["SESS"].keys():
                res+= '<li>%s: ' % item
                try:
                   res+= self.eng.globals["SESS"][item]
                except:
                   res+= '(can\'t unpickle)'
                res+= '</li>\n'
            res+= '</ul>\n'
        res+= "<h2>script output:</h2>\n"
        res+= '<pre class="output">\n' + \
              htmlEncode(self.eng.response.getHeaders()) + \
              htmlEncode(self.eng.response.buffer) + \
              "</pre>\n"
        return res

    def errHeaders(self):
        return trim(
            '''
            Status: 500 Internal Server Error
            Content-Type: text/html; charset=utf-8
            
            ''')

    def errStart(self):
        return trim(
            '''
            <html>
            <head>
            <title>weblib.cgi exception</title>
            <style type="text/css">
                body, p {
                   background: #cccccc;
                   font-family: verdana, arial;
                   font-size: 75%;
                }
                pre { font-size: 120%; }
                pre.traceback { color: red; }
                pre.output{ color : green }
            </style>
            </head>
            <body>
            ''')

    def errFooter(self):
        return trim(
            '''
            <hr/>
            <a href="https://secure.sabren.com/trac/workshop/">weblib</a>
            (c) copyright 2000-2008
            <a href="http://www.sabren.com/">Sabren Enterprises, Inc</a>. 
            All rights reserved.
            </body>
            </html>
            ''')
# * Twisted support
if True:
    class TwistedTest: pass
else:
    import os
    import unittest
    from twisted.test.test_web import DummyRequest
    from weblib.misc import weblibtwisted


    # TODO: move this twisted stuff out of weblib or trash it completely
    class TwistedTest(unittest.TestCase):
        def test_render(self):
            import weblib
            base = os.path.split(weblib.__file__)[0]
            resource = weblibtwisted.RantResource(os.path.join(
                *[base, 'spec', 'twisted.app']), None)
            request = DummyRequest([]) # The url segments below resource to request
            result = resource.render(request)
            self.assert_(result)


# * run the tests
if __name__ == "__main__":
    unittest.main()

