
Model Your Domain
=================

define a class
--------------
from the top level directory::

    /path/to/wks.py model Classname tablename

model one-to-many relationships with ``linkset``
------------------------------------------------
from the top level directory::

    /path/to/wks.py linkset ParentClass linkName ChildClass backLinkName

Creating a linkset automatically creates the back link.


model one-to-one relationships with ``link``
--------------------------------------------
from the top level directory::

    /path/to/wks.py link FromClass linkName ToClass


modelling many-to-many relationships
------------------------------------

Just model these as two separate one-to-many relationships 
on the same junction object.


@TODO: visual modeling
----------------------

draw enough to support the use case
Draw an object model. 

@TODO: would be great if this used drag/drop boxes and arrows

What are the nouns?

Use the `UML colors <http://en.wikipedia.org/wiki/UML_colors>`_:

    * yellow - role
    * pink - moment, interval
    * blue - description
    * green - party,place,thing

