Skins
=====

A platonic app is an application stripped of its user interface.

A skin, then, is a user interface that can be wrapped around the
platonic app.

For example:

   * RESTful API
   * AtomPub
   * Web Applications
       * django
       * rails [via ensemble/http/etc]
       * name your framework
   * command line interface
   * user mode file system for linux ??


The Genshi/Paste/WebAppWorkshop skin
------------------------------------

How to do to it in workshop:

* define the platonic app
* now create a urlmap (should be pretty easy)

def xor(a,b):
   return (a and not b) or (b and not a)

class URI:
    def __init__(uri, app=None, **methods):
        if not xor(app, methods):
            raise TypeError("app/methods are mutually exclusive")
        # ... (same as before)
        
def makeURLMap(app):
    return urlmap(
        URI("/api", RESTfulAPI(app)),
	URI("/people"),


