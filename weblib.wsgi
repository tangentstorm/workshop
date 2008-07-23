#!/usr/bin/python2.5
"""
weblib.wsgi : a wsgi script for weblib
"""
## import sys
## sys.stderr = sys.stdout
## print "content-type: text/plain"
## print

## CONFIGURATION ############################
## use this to add custom lib directories:

#import sys
#sys.path = [".","/home/sei/lib/workshop"] + sys.path

#############################################

import cgi
import os
import os.path
import string
import StringIO
import weblib
import fcgi
from Cookie import SimpleCookie


def urljoin(a, b):
    res = a
    if not res.endswith('/'): res += '/'
    if b.startswith('/'):
        res += b[1:]
    else:
        res += b
    return b

def weblib_app(environ, start_response):

    # lighty calls this "broken-scriptfilename" for php,
    # to be what we want too.. so let's use it, for now.
    path, filename = os.path.split(environ["SCRIPT_FILENAME"])
    #print path, filename
    
    os.chdir(path)
    script = open(filename)

    #import pprint
    #pprint.pprint(environ)
    
    req = weblib.Request(
        method = environ["REQUEST_METHOD"],
        host = environ["SERVER_NAME"],
        path = environ["SCRIPT_NAME"] + environ["PATH_INFO"],
        query = weblib.RequestData(environ["QUERY_STRING"]),
        form = None,
        cookie = SimpleCookie(environ.get("HTTP_COOKIE", "")),
        content = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH", 0))),
        remoteAddress = environ["REMOTE_ADDR"],
    )
    eng = weblib.Engine(script, req)       
    eng.run()
    
    out = weblib.OutputDecorator(eng)

    status = "200 OK"
    headers = [("Content-Type", eng.response.contentType)]
    for k,v in eng.response.headers:
        if k.lower() == "status":
            status = v
        else:
            headers.append((k,v))
            
    start_response(status, headers)
    yield out.getBody()
    
    if eng.hadProblem() and eng.globals["SITE_MAIL"]:
        out.sendError() # send email
        

if __name__=="__main__":
    fcgi.WSGIServer(weblib_app, bindAddress=("127.0.0.1",3000)).run()

