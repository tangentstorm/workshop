
RESTful APIs
------------

Map HTTP's uniform interface to platonic's uniform CRUD interface

GET /whatver       = app['whatever']()
GET /whatver?x=y   = app['whatever'].match(x='y')
GET /whatever/1    = app['whatever'][1]()


What about:

   /whatever/xx/yy ? is it xx.yy? or [xx][yy] or [xx].yy

It really depends on the cardinality of /whatever/:

   /klass/id/prop = app.klass[id].prop
   /obj/prop      = app.obj.prop

Twisted.web used to have resource objects that handled
this and I think that made a lot of sense.

POST /whatever     = app.whatever << formdata     # append (with adaptation)
PUT /whatever/1    = app.whatever[1] = formdata   # assign (with adaptation)
DELETE /whatever/1 = del app.whatever[1]
