import wsgiref.handlers
import traceback
import sys
import cgi

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
