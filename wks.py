"""
wks - command line tool for webAppWorkshop
"""
from __future__ import with_statement
from contextlib import contextmanager
import os
from handy import trim

@contextmanager
def outstream(filename):
    try:
        f = open(filename, "w")
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


    with outstream("dispatch.py") as out:
        out(trim(
            """
            import %s as app
            from platonic import REST,URI
            
            api = REST(
                URI("/", GET= lambda: handler)
            )
            """) % (appname))


    with outstream("schema.py") as out:
        out(trim(
            """
            import model as m
            import clerks
            import storage
            import MySQLdb

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
            

def devserve():
    pass

