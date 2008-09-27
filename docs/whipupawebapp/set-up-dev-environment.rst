
Set Up Your Development Environment
===================================

install dependencies
--------------------
python

setuputils

subversion (for now)

easy_install Paste PasteConfig CherryPy 

easy_install Sphinx Pygments

easy_install MySQL-python

easy_install Genshi



create the application skeleton
-------------------------------

**directory structure** ::

    mkdir sites/$APPNAME
    cd sites/$APPNAME

    mkdir spec
    mkdir tests
    mkdir model
    mkdir theme
    mkdir theme/default


**main module:** $APPNAME.py ::

    __version__="$version$"

**paste config file:** $APPNAME.app ::

    __version__="$version$"

**RESTful API:** restful.py ::

    from platonic import REST,URI
    api = REST(
        URI("/", GET= lambda: handler)
    )


**database map:** dbmap.py

**default layout:** theme/default/layout.gen



Set up Version Control
----------------------

