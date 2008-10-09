
Creating a new project
======================

Optional: Set up Subversion Repository
--------------------------------------

If you're using subversion, you might start like this:

::
    mkdir appname
    cd appname
    mkdir branches
    mkdir tags
    mkdir trunk
    cd trunk


Create the application skeleton
-------------------------------

::
    /path/to/workshop-trunk/wks.py init appname

Define a Database Connection
----------------------------
Edit appname.app

If you're using an engine besides MySQL, change the
generated code in schema.py.
