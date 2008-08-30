"""
Paste-compatable factory that builds a CherryPy WSGI server.

The reason for using cherry's server is that it doesn't put
require extra coding to enable RESTful HTTP methods like
PUT/DELETE/etc.

Example usage (in your paste config file):

[server:main]
paste.server_factory = cherrypaste:server_factory
host = panther
port = 8080

"""
from cherrypy.wsgiserver import CherryPyWSGIServer
import socket

def server_factory(global_conf, host, port):

    # compensate for cherrypy's screwy handling of host names.
    # (it insisted on mapping my server name to localhost)
    addr = socket.gethostbyname(host)
    port = int(port)

    def serve(app):
        cherry = CherryPyWSGIServer((addr, port), app, server_name=host)
        cherry.start()

    return serve
