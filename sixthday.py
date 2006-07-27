from handy import sendmail, trim
from strongbox import attr, Strongbox, link, linkset, BoxView
from clerks import Clerk, Schema, MockClerk
from storage import MockStorage
import cStringIO
import handy
import os
import weblib
import zebra
import unittest
from weblib import Finished
from sesspool import Sess, InMemorySessPool
import string

# * App
class AppTest(unittest.TestCase):

    def setUp(self):
        if hasattr(weblib, "request"):
            self._REQ = weblib.request


    def tearDown(self):
        if hasattr(self, "_REQ"):
            weblib.request = self._REQ


    def test_input(self):

        ## used to rely on weblib.request.. now should NOT
        weblib.request = {"GOAL":"GOAL"}
        actor = App({})
        assert actor.input == {}, \
               "Wrong default input when weblib.request IS defined:\n%s" \
               % actor.input
        del weblib.request

        actor = App({})
        assert actor.input == {}, \
               "Wrong default input when weblib.request IS NOT defined"

        actor = App({"red":"blue"})
        assert actor.input == {"red":"blue"}, \
               "Wrong .input when input is supplied"
        

    def test_act_(self):

        class Shakespearean(App):
            def act_(self):
                ToBe = "?"
                self.question = ToBe or (not ToBe)
        
        hamlet = Shakespearean({})
        hamlet.question = None
        hamlet.act()

        assert hamlet.question == "?", \
               "act() doesn't default to calling act_(). :("
               
    def test_write(self):
        devito = App({})
        goal = "what's the worst that could happen?"
        devito.write(goal)
        actual = devito.act()
        assert actual == goal, \
               "Actor.write() doesn't work. got: %s" % actual


    def test_jump(self):
        brando = App({})
        self.assertRaises(weblib.Redirect,
                          brando.redirect, action="somewhere")
        


"""
A base class for web pages that act differently based on a parameter.
"""

#@TODO: subclass that uses Signature to pass values to act_XXX?

class App(object):
    """
    App(input) where input=a dict, usually with a key called 'action'.
    
    This class is designed to make it easy to write classes that can
    be called directly through a URL. It's just a base class, and only
    provides enough logic to handle dispatching actions right now.    
    
    The input dict should have a key called "action" that will tell the
    actor what to do. The App subclass must have a method caled act_XXX
    where XXX is whatever "action" mapped to.
    """

    ##@TODO: a generic nextMap for action chains might come in handy,
    ## and keep people from having to override every little method.

    ## constructor ################################################

    def __init__(self, input):
        self.debug = 0 # alters behavior of complain()

        self._copyinput(input)

        # out is just a buffer:
        self.out = cStringIO.StringIO()

        # where is a special variable that tells you where
        # you can jump. It's basically a way to let you
        # redirect pages as you see fit via act_jump
        # without letting anyone use your page to redirect
        # things arbitrarily..
        self.where = {}
        
        self.action = None
        self.next = None
        self.errors = []
        self.model = {"errors":[]}
        for key in self.input.keys():
            self.model[key] = self.input[key]

    def _copyinput(self, input):
        self.input = {} # so we can call do() with extra params
        try:
            for k in input.keys():
                self.input[k] = input[k]
        except AttributeError, e:
            raise "invalid input: %s" % `input`
            


    ## public methods ############################################

    def enter(self):
        """
        Override this with stuff to do before acting. called by act().
        """
        pass


    def exit(self):
        """
        Override this with stuff to do after acting. called by exit().
        """
        pass
    

    def act(self, action=None):
        """
        ex: actor.act();   actor.act('jump')
        returns output buffer built by calls to write()

        ## @TODO: clean up this whole 'next' concept..
        ## looks like it was set up to tell the client to
        ## reinvoke act(). But it's basically a giant,
        ## nasty GOTO feature and must be killed!
        """

        if action is not None:
            self.action = action
        else:
            self.action = self.input.get("action", "")

        self.enter()
        self.next=self.action
        while self.next is not None:
            next = self.next
            self.next = None
            if type(next)==type(""):
                self.do(next)
            else:
                raise TypeError, "next should not be... %s" % `next`
        self.exit()
        return self.out.getvalue()


    def do(self, action, input=None, **params):
        """
        like act(), but doesn't do enter/exit stuff..
        handy if you want an action to call another action
        """
        if input is not None:
            self._copyinput(input)
        for key in params.keys():
            self.input[key]=params[key]

        oldaction = self.action
        if action is not None:
            self.action = action
            
        if type(self.action) == type(()):
            raise TypeError, 'Multiple actions requested: %s' \
                  % str(self.action)

        method = getattr(self, "act_" + self.action, None)
        assert method, "don't know how to %s" % self.action
        method()
        self.action = oldaction

    def complain(self, problems):
        """
        Generic error handler. Pass it a string or list of strings.
        """
        if type(problems)==type(""):
            probs = [problems]
        else:
            probs = problems
        for prob in probs:
            self.errors.append(prob)
            self.model["errors"].append({"error":prob})
            if self.debug:
                print >> self, "\n::<b>ERROR</b>::", prob

    def consult(self, model):
        """
        updates the App's internal model based on the
        passed in model. model can be either a module
        name or a dict.

        if it's a module name, the module should contain
        a dict called model.
        """
        # models and modules.... heh... :)
        if type(model) == type(""):
            self.model.update(__import__(model).model)
        else:
            # assume it's a dict of sorts:
            for item in model.keys():
                self.model[item] = model[item]


    def redirect(self, url=None, action=None):
        """
        Sets self.next and throws weblib.Redirect
        """
        if not ((url is not None) ^ (action is not None)):
            raise TypeError, "syntax: actor.redirect(url XOR action)"
        if url:
            where=url
            self.next = None
        else:
            #@TODO: why __weblib_ignore_form__ again?
            where="?action=%s&__weblib_ignore_form__=1" % (action)
            self.next = action
        raise weblib.Redirect, where


    def map_where(self, where):
        """
        Given a shortname, returns a url. Used to prevent
        people from redirecting randomly through pages.

        Returns None if no URL found.
        """
        return self.where.get(where)


    def write(self, what):
        """
        write something to output..
        """
        self.out.write(what)


    ## actions ###################################################

    def act_(self):
        """
        Default action. Does nothing, but you can override it.
        """
        pass

# * Auth
class AuthTest(unittest.TestCase):

    def setUp(self):
        self.myReq = weblib.RequestBuilder().build(
            method="GET",querystring="",
            path="/",
            form={},
            cookie={},content={})
        self.myRes = weblib.Response()
        self.sess = Sess(InMemorySessPool(), self.myReq, self.myRes)

    def test_check(self):
        try:
            auth = Auth(self.sess, {})
            auth.check()
            gotExit = 0
        except Finished:
            gotExit = 1
        assert gotExit, \
               "didn't get systemExit (from response.end)"
        assert string.find(self.myRes.buffer, Auth.PLEASELOGIN), \
               "check doesn't show login screen"
        

    def test_login_invalid(self):
        """
        Invalid login should show error, display form, and raise Finished.
        """
        req = weblib.RequestBuilder().build(
            querystring="auth_check_flag=1",
            path="/",
            form={"auth_username":"wrong_username",
                  "auth_password":"wrong_password"})
        sess = Sess(InMemorySessPool(), req, self.myRes)
        try:
            auth = Auth(sess, {'username':'password'})
            auth.check()
            gotExit = 0
        except Finished:
            gotExit = 1
        assert gotExit, \
               "invalid login didn't get Finished"
        assert string.find(self.myRes.buffer, auth.LOGINFAILED) > -1, \
               "invalid login doesn't give LOGINFAILED!"



    def test_login_valid(self):
        """
        Valid login should have no side effects.
        """
        req = weblib.RequestBuilder().build(
            querystring="auth_check_flag=1",
            path="/",
            form={"auth_username":"username",
                  "auth_password":"password"})
        sess = Sess(InMemorySessPool(), req, self.myRes)
        try:
            auth = Auth(sess, {"username":"password"})
            auth.check()
            gotExit = 0
        except Finished:
            gotExit = 1
        assert self.myRes.buffer == "", \
               "valid login shouldn't output anything! [vs '%s']" \
               % self.myRes.buffer
        assert not gotExit, \
               "valid login still threw Finished"


    # @TODO: write tests for this stuff:
        
    def notest_Logout(self):
        pass

    def notest_Fetch(self):
        pass

    def notest_Validate(self):
        pass

    def notest_EncodeNormal(self):
        pass

    def notest_EncodePassword(self):
        pass
    
    def notest_Recovery(self):
        pass

    def notest_Persistence(self):
        pass
    
    def tearDown(self):
        pass
        #del self.auth 

"""
Auth.py - generic authentication framework for python cgi.
"""

#@TODO: license, etc..

## Auth class #################################

class Auth:
    """
    Generic Authentication class for the web. This is loosely
    based on Auth.inc from PHPLIB.
    """

    LOGINFAILED = 'Login failed.'
    PLEASELOGIN = 'Please log in.'

    _isStarted = 0

    ## constructor #############################
    
    def __init__(self, sess, userdict):
        """
        usage: auth=Auth(sess, userdict)
        where userdict is like {'usr1':'pwd1','usr2':'pwd2'...}
        """
        self._sess = sess
        self._users = userdict


    ## public methods #########################

    def start(self, key=None):
        #@TODO: is there any reason why this shouldn't be in __init__?

        self._isStarted = 1
        self.isLoggedIn = 1 # assume the best

        if key:
            self.key = key
        elif self._sess.has_key('__auth_key'):
            self.key = self._sess['__auth_key']
        else:
            self.isLoggedIn = 0 # oh well.

    def check(self):
        """
        Make sure the user is authenticated.
        If not, prompt for credentials.
        """

        if not self._isStarted:
            self.start()
        
        if self._sess._request.query.has_key('auth_logout_flag'):
            self.logout()

        if not self.isLoggedIn:
            if self._sess._request.query.has_key('auth_check_flag'):
                if self._attemptLogin():
                    self.onLogin() # they're in!
                else:
                    self.prompt(Auth.LOGINFAILED, self._getAction(),
                                self._getHidden())
                    self._sess._response.end()
            else:
                self.prompt(Auth.PLEASELOGIN, self._getAction(),
                            self._getHidden())
                self._sess._response.end()
        else:
            self.login(self.key) 
    

    def login(self, key):
        """
        Force a login with the specified key.
        """
        self.key = key
        self.fetch(self.key)
        self._sess['__auth_key'] = self.key
        self.onLogin()

                
    def logout(self):
        """
        Logs out the current user.
        """
        self.onLogout()
        self.isLoggedIn = 0
        self.key = None
        if self._sess.has_key('__auth_key'):
            del self._sess['__auth_key']
                    


    ## abstract methods ########################
    
    def fetch(self, key):
        pass # raise AbstractError ?


    def validate(self, dict):
        """
        This should test whether the credentials in dict are valid,
        and if so, return a key, else return None
        """

        # example implementation for testing, based on form below:

        authKey = None
        if (dict.get("username") in self._users.keys()) \
           and (dict.get("password") == self._users[dict["username"]]):
            authKey = dict["username"]
        return authKey


    def prompt(self, message, action, hidden):
        """
        This should show an HTML prompt and call response.end().
        You should overwrite this!
        """

        self._sess._response.write("""
        <h1>%s: %s</h1>
        <form action="%s" method="post">
        username: <input type="text" name="auth_username"><br>
        password: <input type="password" name="auth_password"><br>
        <input type="submit">
        %s
        </form>
        """ % (self.__class__.__name__, message, action, hidden))
        


    def transform(self, field, value):
        """
        Overwrite this if you want to eg, encode/encrypt credentials
        before passing to validate()
        """

        return value



    ## events (overwritable) ##################

    def onLogin(self):
        """
        overwritable onLogin event.
        """
        pass

    def onLogout(self):
        """
        overwritable onLogout event.
        """
        pass

    
    ## internal methods #######################
    
    def _attemptLogin(self):
        """
        Gets stuff from the login form and passes it to validate..
        """

        dict = {}
        res = 0

        # first move all the auth_* variables into a hash,
        # transforming them along the way.
        
        for item in self._sess._request.keys():
            if item[:5] == "auth_":
                dict[item[5:]] = self.transform(item[5:],
                                                self._sess._request[item])

        # now pass it to validate() and see if we get in:
        self.key = self.validate(dict)
        if self.key is not None:
            self.login(self.key)
            res = 1

        return res


    def _getAction(self):
        """
        Returns a string with the current URL and coded querystring.
        This is used for the ACTION property of the login form.
        """
        res = self._sess._request.path + "?auth_check_flag=1"
        for item in self._sess._request.query.keys():
            if item[:5] == "auth_":
                pass # IGNORE old auth stuff
            else:
                res = res + "&" + weblib.urlEncode(item) + \
                      "=" + weblib.urlEncode(self._sess._request.query[item])
        return res

    

    def _getHidden(self):
        """
        This function builds a string containing hidden form fields.
        
        This is because the session could expire while someone is working
        on a form. If they post the form, they should get a login-box,
        but we want to remember their data while they're logging back in!
        """
        res = ""
        for item in self._sess._request.form.keys():
            # form should be an IdxDict..
            if item[:5] == "auth_":
                pass # Ignore auth stuff here, too
            else:
                # value should either be a string or a tuple
                # of strings. (for multi-select boxes or whatever)
                if type(self._sess._request[item]) == type(()):
                    # for tuples, loop through all the values:
                    for subitem in self._sess._request[item]:
                        res = res + '<input type="hidden" name="' + \
                              weblib.htmlEncode(item) + '" value="' + \
                              weblib.htmlEncode(subitem) + \
                              '">\n'
                elif item != 'sesspool.Sess': #@TODO: is this right?
                    # only one value:
                    res += '<input type="hidden" name="'
                    res += weblib.htmlEncode(item) + '" value="'
                    res += weblib.htmlEncode(str(self._sess._request[item]))
                    res += '">\n'
                else:
                    pass

        return res
# * AdminApp
class AdminAppTest(unittest.TestCase):

    def setUp(self):

        self.storage = MockStorage()
        self.clerk = Clerk(self.storage, Schema({
            User: "User"
        }))
        self.app = AdminApp(self.clerk, {})
        
        # set up some templates to play with:
        tpl = open("frm_test.zb", "w")
        tpl.write("ID is {:ID:}")
        tpl.close()

        tpl = open("lst_test.zb", "w")
        tpl.write(
            "*# zebra to print a dot for each user:\n"
            "* for each:\n" 
            "    {:x:}\n")
        tpl.close()
        
    def test_generic_create(self):
        """
        generic_create should show a page with a view of a new object.
        """
        self.app.generic_create(User, "frm_test")
        output = self.app.out.getvalue()
        assert output.startswith("ID is None"), \
               "generic_create didn't populate form correctly:\n%s" \
               % output


    def test_generic_show(self):
        """
        generic_edit should show a form with a specific object's data
        """
        self.test_generic_save()
        self.app.input = {"ID":1}
        self.app.generic_show(User, "frm_test")
        output = self.app.out.getvalue()
        assert output.startswith("ID is 1"), \
               "generic_show didn't populate the page correctly:\n%s" \
               % output

    def test_generic_list(self):
        #@TODO: this method should probably go away.
        view = [{"x":"a"}, {"x":"b"}]
        self.app.generic_list(view, "lst_test")
        output = self.app.out.getvalue()
        assert output.startswith("a\nb"), \
               "generic_list didn't populate the form correctly:\n%s" \
               % output

    def test_generic_save(self):
        self.app.generic_save(User)
        obj = self.clerk.fetch(User, 1)

    def test_generic_delete(self):
        self.storage.store("User", username="fred")
        self.app.input = {"ID":1}
        self.app.generic_delete(User)
        assert self.storage.match("User") == []

   
    def tearDown(self):
        os.unlink("frm_test.zb")
        os.unlink("lst_test.zb")


"""
AdminActor - base class for apps that want to let you edit zdc.RecordObjects

dispatches the following actions: list, show, edit, create, delete

example: to let you list and edit Widgets:

- define a 'lst_widget.zb' zebra file with the html to list widgets
- define a 'dsp_widget.zb' zebra file with the html to show a single widget
- define a 'frm_widget.zb' zebra file with the form to add/edit a single widget
- define the widget AdminActor, like so:

class WidgetAdminActor(AdminActor):

    def list_widget(self):
        view = zdc.select(Widget)
        self.generic_list(view, 'lst_widget')
        
    def show_widget(self):
        self.generic_show(Widget, 'dsp_widget')

    def edit_widget(self):
        # edit is really just show with a different html view
        self.generic_show(Widget, 'frm_widget')
        
    def create_widget(self):
        # create is just edit with a new widget (no ID in url)
        self.generic_create(Widget, 'frm_widget')

    def save_widget(self):
        self.generic_create(Widget, 'frm_widget')

    # no delete_widget, so user can't delete...


"""
__ver__="$Id: AdminApp.py,v 1.4 2002/09/23 22:52:54 sabren Exp $"


class AdminApp(App):

    def __init__(self, clerk, input):
        super(AdminApp, self).__init__(input)
        self.clerk = clerk

    ## list ###################################################
    
    def act_list(self):
        self._dispatch("list")

    def generic_list(self, listOfDicts, template):
        self.model["each"] = listOfDicts
        self._runZebra(template)
        

    ## show/edit/create ###############################################

    def act_show(self):
        self._dispatch("show")

    def act_edit(self):
        self._dispatch("edit")

    def act_create(self):
        self._dispatch("create")

    def generic_show(self, klass, template):
        self._showObject(self._getInstance(klass), template)

    def generic_create(self, klass, template):
        self._showObject(klass(), template)

    ## delete  ######################################################
            
    def act_delete(self):
        self._dispatch("delete")

    def generic_delete(self, klass, nextAction=None):
        self.clerk.delete(klass, self.input["ID"])
        if nextAction:
            self.redirect(action=nextAction)


    ## save ########################################################

    def act_save(self):
        self._dispatch("save")

    def generic_save(self, klass):
        obj = self._getInstance(klass)
        return self.clerk.store(obj)


    ###[ private methods ]###########################################


    def _getInstance(self, klass):
        if self.input.get("ID"):
            obj = self.clerk.fetch(klass, self.input["ID"])
        else:
            obj = klass()
        obj.noisyUpdate(**self.input)
        return obj
        
    def _dispatch(self, action):
        what = self.input.get("what", "")
        meth = getattr(self, "%s_%s" % (action, what), None)
        if meth:
            meth()
        else:
            self.complain("don't know how to %s %s" % (action, what))


    def _runZebra(self, template):
        try:
            print >> self, zebra.fetch(template, self.model)
        except IOError:
            self.complain("unable to load %s.zb" % template)


    def _showObject(self, obj, template):
        self.consult(BoxView(obj))
        self.consult(self.input) # so we can pre-populate via url
        self._runZebra(template)
# * User

class User(Strongbox):

    ID = attr(long, default=None)
    uid = attr(str)
    username = attr(str)
    email = attr(str)
    password = attr(str)
    
    def __init__(self, **init):
        super(User, self).__init__(**init)
        if not self.uid: self.uid = handy.uid()
# * Node
class NodeTest(unittest.TestCase):

    def setUp(self):
        self.clerk = MockClerk(Schema({
            Node: "Node",
            Node.parent: "parentID",
            Node.children: "parentID",
            }))
        s = self.clerk.storage
        
        # we use the storage object so we can define the
        # database without dealing with read-only attribures (path)
        s.store("Node", name='top', path='top', parentID=0)
        s.store("Node", name='sub', path='top/sub', parentID=1)
        s.store("Node", name='subsub', path='top/sub/sub', parentID=2)

        #import pdb; pdb.set_trace()

    def test_crumbs(self):
        node = self.clerk.fetch(Node, 1)
        assert node.crumbs == [], \
               "Didn't get right crumbs for node 1."

        node = self.clerk.fetch(Node, ID=3)
        goal = [{"ID": 1,  "name": "top",  "path": "top"},
                {"ID": 2,  "name": "sub",  "path": "top/sub"}]
        assert len(node.crumbs) == len(goal), \
               "Didn't get right crumbs for node 3."
        

    def test_path(self):
        node = self.clerk.fetch(Node, 2)
        node.name="subnode"
        node = self.clerk.store(node)
        assert node.path == "top/subnode", \
               "Node has wrong path after name change: %s" % node.path


    def test_parent(self):
        node = self.clerk.fetch(Node, 2)
        assert isinstance(node.parent, Node), \
               ".parent doesn't return a Node"    


"""
Generic class for hierarchical structures.
"""
class Node(Strongbox):
    ID = attr(long)
    name = attr(str)
    path = attr(str)
    data = attr(str)
    parent = link(lambda : Node)
    children = linkset((lambda : sixthday.Node), "parent")

    def __init__(self, **kwargs):
        super(Node, self).__init__()
        self.private.named = False
        self.update(**kwargs)
       
##     def set_path(self, value):
##         # only allow setting once
##         if self.private.path:
##             raise AttributeError, "Node.path is read only"

    def get_crumbs(self):
        res = []
        node = self
        while node.parent:
            node = node.parent
            res.append( node )
        res.reverse()  # crumbs go top-down, but we went bottom-up :)
        return res
        
##     def set_parent(self, value):
##         assert value is not self, \
##                "A node can't be its own parent!"

    def set_name(self, value):
        self.private.name=str(value)
        # this .private.named thing prevents a max
        # bug of some kind. It probably needs a
        # closer look.
        if self.private.named:
            self._updatePath(self.crumbs)
        self.private.named = True

        
    def _updatePath(self, crumbs):
        path = crumbs + [self]
        self.path = "/".join([n.name for n in path])
        for kid in self.children:
            kid._updatePath(path)

Node.parent.type=Node
Node.children.type=Node
# * Form

class Model(Strongbox):
    name = attr(str)
    age  = attr(int, default=None)
    prefill = attr(str, default="example")
    limited = attr(str, okay=["a","b","c"], default="a")
    

class FormTest(unittest.TestCase):

    def testInterface(self):
        f = Form(Model())
        assert f["name"] == ""
        assert f["age"] is None
        assert f["prefill"] == "example"

    def testBothways(self):
        f = Form(Model())
        f.model.name = "fred"
        assert f["name"] == "fred"
        f["name"] = "rufus"
        assert f.model.name == "rufus"
        assert f["name"] == "rufus"

    def testValidation(self):
        f = Form(Model())
        try:
            gotError = 0
            f.update({"limited":"bad value",
                      "age":"bad type",
                      "sparky":"bad field"})
        except ValueError:
            gotError = 1

        assert gotError, "expected ValueError"
        assert "age" in f.errors
        assert "limited" in f.errors
        assert "sparky" not in f.errors

    def test_isComplete(self):
        f = Form(Model())
        f.require("age")
        assert not f.isComplete()
        f["age"] = 15
        assert f.isComplete()
        f.require("name","prefill")
        assert not f.isComplete()
        f["name"] = "fred"
        assert f.isComplete()

    def test_keys(self):
        f = Form(Model())
        keys = list(f.keys())
        keys.sort()
        assert keys == ["age","limited","name","prefill"], keys

        # and for non-strongboxes...
        # (YAGNI, probably, but it might help someone else)
        class Gronk: pass
        g = Gronk()
        g.a = 1
        g.b = 2
        g.c = 3
        g._ = "hidden"
        f = Form(g)
        keys = list(f.keys())
        keys.sort()
        assert keys == ["a","b","c"]

    def test_ToDict(self):
        f = Form(Model())
        assert f.toDict() == {"name":"",
                              "age":None,
                              "prefill":"example",
                              "limited":"a"}


#@TODO: AdminApp should use this Form object.
#@TODO: Form should replace (subclass?) BoxView.

class Form:
    """
    I provide dictionary-like access to my model
    and check it for required fields
    """
    def __init__(self, model):
        self.model = model
        self.errors = {}
        self.required = []

    ## dictionary interface #############

    def __getitem__(self, key):
        return getattr(self.model, key)

    def __setitem__(self, key, value):
        setattr(self.model, key, value)

    def update(self, data):
        self.errors = {}
        for k,v in data.items():
            if hasattr(self.model, k):
                try:
                    setattr(self.model, k, v)
                except (ValueError, TypeError), e:
                    self.errors[k]="Invalid %s: %s" % (k, v)
        if self.errors:
            raise ValueError, "invalid data, see self.errors"

    def keys(self):
        if hasattr(self.model.__class__, "attrs"):
            return self.model.__class__.attrs
        else:
            return tuple([a for a in dir(self.model) if not a.startswith("_")])

    ## extra stuff ######################

    def toDict(self):
        d = {}
        for field in self.keys():
            d[field] = self[field]
        return d
        

    def require(self, *fields):
        for field in fields:
            self.required.append(field)

    def isComplete(self):
        res = True
        for field in self.required:
            if getattr(self.model, field) in ["",None]:
                self.errors[field] = "A value is required for %s." % field
                res = False
        return res


# * --
if __name__=="__main__":
    unittest.main()
