
Platonic
========

Platonic is a way of composing applications
independently from their user interface. 

Platonic applications:

   * employ a RESTful architecture
   * use a strict naming convention
   * can be composed into larger applications
   * are aware of users, roles, and permissions
   
The platonic framework itself is written in python,
but individual components can be written in practically
any language.

.. toctree::
   crud
   rest
   auth
   perm
   skin


RESTful Python
--------------

The four verbs of HTTP map easily to python
semantics. (POST is a bit tricky, but we'll 
overload the << operator for that)

    GET    : app.xxx
    PUT    : app.xxx = content
    POST   : app.xxx << content
    DELETE : del app.xxx

Also, URL mapping is fairly easy:

    /uri?query : app.xxx(query)
    /uri/pa/th : app.xxx[pa][th]


So.. Is it possible to discover which operations are available?

    GET    : always available? [but may just return docstring?]
    PUT    : you'd have to wrap with setattr.. maybe tag with a decorator?
    POST   : implements __lshift__
    DELETE : DELETE

Basically, you could just try it, and if it doesn't work,
there should be a standard response for the error code.

@TODO: but how do you implement OPTIONS?
