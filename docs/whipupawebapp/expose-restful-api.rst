
Expose a RESTful API
====================

Define URIs
-----------
.. python

   self.rest = REST(
     URI("/posts/(?P<ID>[0-9]+)$",
         PUT=lambda...))



Implement the Method Handlers
-----------------------------
@TODO: CRUD should be generic.

.. python
   # in $APPNAME.py:
   class StorePostCommand(object):
       def invoke(self, _clerk, ID):
          
   _clerk.fetch(Post, int(ID) )
   Post.update(xxxx)
   _clerk.store(Post)


The POST Tunnel
---------------
<input type="hidden" name="@method" value="PUT"/>
<input type="text" name="_content"/>

no browser support for PUT, so: tunnel through post with:

.. code html
   <form action="/whatever" method="post">
     <fieldset>
	<legend></legend>
        <input type="hidden" name="@method" value="PUT"/>
     </fieldset>
   </form>


start the server
----------------
paster serve --reload $APPNAME.app


create .htaccess for apache mode
--------------------------------


