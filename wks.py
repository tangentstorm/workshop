"""
wks - command line tool for webAppWorkshop
"""
from __future__ import with_statement
from contextlib import contextmanager
import os, sys
import __main__
from handy import trim, genshiText, xml, indent


@contextmanager
def outstream(filename, mode="w"):
    try:
        f = open(filename, mode)
        yield f.write
    finally:
        f.close()


def init(appname):
    os.mkdir(appname)
    os.chdir(appname)

    dirs = ['spec','test','model','theme','theme/default']
    for d in dirs:
        os.mkdir(d)

    appClass = appname.capitalize() + "App"

    with outstream("%s.py" % appname) as out:
        out(trim(
            '''
            import model, schema
            from dispatch import urlmap
            from wsgiapp import WebApp, GenshiTheme, fileHandlerFactory
            
            __version__="$version$"

            def app_factory(cfg, dbhost, dbname, dbpass, dbuser, baseURL,**etc):
                """
                entry point for paste
                """
                clerk = schema.makeClerk(dbhost, dbuser, dbpass, dbname)
                return %(appClass)s

            class %(appClass)s(WebApp):
                def __init__(self, baseURL, urlmap, clerk=None):
                    super(%(appClass)s, self).__init__(
                        baseURL,
                        [urlmap, fileHandlerFactory])
                    self.theme = GenshiTheme(baseURL)
                    self.clerk = clerk or schema.mockClerk()
                    
            ''') % dict(appClass=appClass))

    
    with outstream("%s.app.in" % appname) as out:
        out(trim(
            """
            #!/bin/env paster
            # $version$

            [server:main]
            paste.server_factory = cherrypaste:server_factory
            host = localhost
            port = 8080
            baseURL = http://localhost:8080/

            [app:main]
            paste.app_factory = %(app)s:app_factory
            
            dbhost = %(dbhost)s
            dbname = %(dbname)s
            dbuser = %(dbuser)s
            dbpass = %(dbpass)s

            """) % dict(app=appname,
                        dbhost='localhost',
                        dbname=appname,
                        dbuser=appname,
                        dbpass=appname))


    with outstream("model/__init__.py", "a") as out:
        out('')

    with outstream("dispatch.py") as out:
        out(trim(
            """
            import %s as app
            from platonic import REST,URI
            
            urlmap = REST(
                URI("/", GET= lambda: handler)
            )
            """) % (appname))


    with outstream("schema.py") as out:
        out(trim(
            """
            import clerks
            import storage
            import MySQLdb
            from model import *

            schema = clerks.Schema({
            })

            def connect(dbhost, dbuser, dbpass, dbname):
                return MySQLdb.connect(
                    user = dbuser,
                    passwd = dbpass,
                    host = dbhost,
                    db = dbname)

            def makeClerk(dbhost, dbuser, dbpass, dbname):
                dbc = connect(dbhost, dbuser, dbpass, dbname)
                return clerks.Clerk(storage.MySQLStorage(dbc), schema)

            def mockClerk():
                return clerks.MockClerk(schema)

            """))


    with outstream('theme/default/layout.gen') as out:
        out(trim(
            '''
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
                      "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head>
            <meta http-equiv="Content-Type"
                content="text/html; charset=utf-8" />
            <title>${title}</title>
            <link rel="stylesheet" href="style.css"/>
            </head>
            <body>
            
            <h1>${title}</h1>
            
            </body>
            </html>
            '''))


    with outstream('theme/default/style.css') as out:
        out(trim(
            """
            body {
              color: black;
              background: white;
              font-family:Verdana, Arial, Helvetica, sans-serif;
              font-size: 10pt;
            }
            """))


def currentAppName():
    if not os.path.exists("model"):
        raise SystemExit("please run from app directory (model directory not found)")
    return os.path.split(os.getcwd())[-1]


def addToSQL(sql):
    # @TODO: actuall run the sql!
    with outstream("%s.sql" % currentAppName(), "a") as out:
        out(sql)


def modelClassExists(className):
    return os.path.exists("model/%s.py" % className)


def addToModel(className, tableName=None):
    """
    Adds a class to the model.
    """
    appname = currentAppName()
    if not className[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        raise SystemExit("class must start with uppercase letter")

    if modelClassExists(className):
        raise SystemExit("class %s.model.%s already exists."
                         % (appname, className))

    tableName = tableName or className.lower()
    addToSQL(trim(
        '''
        CREATE TABLE %s (
            ID INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY
        );
        ''') % tableName)

    with outstream("test/%sTest.py" % className) as out:
        out(trim(
            """
            from %s import model
            import unittest
            from strongbox import *
            
            class %sTest(unittest.TestCase):
        
                def setUp(self):
                    pass

                def test_constructor(self):
                    obj = %s()

                def tearDown(self):
                    pass

            if __name__ == '__main__':
                unittest.main()
            """) % (appname, className, className))


    with outstream("model/%s.py" % className) as out:
        out(trim(
            """
            from strongbox import *
            from pytypes import *
            import model
            
            class %s(Strongbox):
                ID = attr(long)
            """) % className)

    with outstream("model/__init__.py", "a") as out:
        out(trim(
            """
            from %s import %s
            """ % (className, className)))


    addToSchema(className, repr(tableName))



def addToSchema(key, value):
    lines = open("schema.py").readlines()
    state = 'start'
    for i, line in enumerate(lines):
        if line.startswith('schema ='):
            state = 'in-schema'
        elif state=='in-schema' and line.startswith("})"):
            lines.insert(i, '    %s : %s,\n' % (key, value))
            break
        else: pass
    else:
        raise SystemExit("couldn't add line to schema.py! [end state: %s]" % state)
    with outstream("schema.py") as out:
        out(''.join(lines))


def getTableForClass(className):
    import schema, model
    return schema.schema.dbmap[getattr(model, className)]    

def expectModelClass(name):
    if not os.path.exists("model/%s.py" % name):
        raise SystemExit("class %s not found in model" % name)

def addLinkset(parent, linksetName, child, backlink=None):
    expectModelClass(parent)
    expectModelClass(child)
    #@TODO: auto-generate a test case for linkset
    with outstream("model/%s.py" % parent, "a") as out:
        out('    %s = linkset(lambda: model.%s, "%s")\n'
            % (linksetName, parent, backlink))
        
    if backLink:
        addLink(child, backlink, parent)


def addLink(fromClass, linkName, toClass):
    #@TODO: auto-generate a test case for link
    expectModelClass(fromClass)
    expectModelClass(toClass)
    with outstream("model/%s.py" % fromClass, "a") as out:
        out('    %s = link(lambda: model.%s)\n'
           % (linkName, toClass))

    foreignKey = "%sID" % linkName
    addToSchema("%s.%s" % (fromClass, linkName), repr(foreignKey))
    addToSQL('ALTER TABLE %s ADD COLUMN %s INTEGER NOT NULL DEFAULT 0;\n'
             % (getTableForClass(fromClass), foreignKey))





code_for_attr = genshiText(
    "$name = attr($type${', default=%s' % default if default else ''})\n")


def fromXMI(filename):
    """
    generates workshop-flavored python from xmi
    """
    NS = {
        "xmi": "http://schema.omg.org/spec/XMI/2.1",
        "uml": "http://schema.omg.org/spec/UML/2.0",
    }
    doc = xml(open(filename).read())

    for node in doc.xpath("//@xmi:type[string()='uml:Class']/..", NS):
        className = node.xpath("string(@name)")

        if modelClassExists(className):
            print "skipping existing class %s" % className

        else:
            addToModel(className, className.lower())
            with outstream("model/%s.py" % className, 'a') as out:
                for attr in node.xpath("ownedAttribute"):
                    out(indent(code_for_attr(
                            name = attr.xpath("string(@name)"),
                            type = attr.xpath('string(@type)')[:-3] or 'str',
                            default = attr.xpath('string(defaultValue/@value)'))))

            print "added class %s" % className
    

def expectArg(argv, index, msg):
    try:
        return argv[index]
    except:
        raise SystemExit("usage: %s" % msg)

def allowArg(argv, index):
    return argv.get(index)

def makeArgParser(usage):
    args = usage.split()
    cmd  = args[0]
    func = getattr(__main__, cmd)
    return cmd, lambda argv: func(*[
        allowArg(argv, 2+i) if slot.startswith("[")
        else expectArg(argv, 2+i, usage)
        for i,slot in enumerate(args[1:])])


def main(argv):
    cmds = dict(makeArgParser(line) for line in trim(
        """
        init appname
        addToModel ClassName [tableName]
        addLink  FromClass linkName ToClass
        addLinkset ParentClass linksetName ChildClass [backLinkName]
        fromXMI filename
        """).split('\n') if line)

    usage = "usage: wks [ %s ]" % (' | '.join(sorted(cmds.keys())))
    cmd = expectArg(argv, 1, usage)
    if cmd in cmds:
        cmds[cmd](argv)
    else:
        raise SystemExit(usage)

if __name__ == '__main__':
    main(sys.argv)

