
Model Your Domain
=================


draw enough to support the use case
-----------------------------------

Draw an object model. 

@TODO: would be great if this used drag/drop boxes and arrows

What are the nouns?

Use the `UML colors <http://en.wikipedia.org/wiki/UML_colors>`_:

    * yellow - role
    * pink - moment, interval
    * blue - description
    * green - party,place,thing


define a class
--------------

import unittest
from strongbox import *

class Whatever(Strongbox):
    ID = attr(long)

if __name__=="__main__":
    unittest.main()


add an attribute
----------------

model a one-to-one relationship with Link
-----------------------------------------

model a one-to-many relationship with LinkSet
----------------------------------------------
optional


modelling many-to-many relationships
------------------------------------

