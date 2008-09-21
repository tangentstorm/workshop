from trailblazer import BlazeHound


# our table of contents:

contents = [

    "platonic",
    "webapp",

    # email stuff:
    "contact", # simple form handler

    # look and feel
    "reptile",

    # data management apps
    "approach",    
    "entries",  # start with a simple blog
    "blogroll",  # introduce storage module
    # multiple blogs # joins
    # categories : 
    # schemas : generating the sql... from strongbox??
    "fields", # generic form handler 
    #* validation: strongbox
    #* skinning / custom templates
    #* triggers : index, etc.
    # lazy loading

#* dropdowns: okay
#* normalize users and areas: multiple tables
#* permissions: ID should be a convention, not a hard coded idea
#* cross site scripting
#* annotations / amorphous db
#* rdf 

    # content management
    "nodak",

    # alltogether now:
    "rantelope",
]


def getSolution(makeHTML=False):
    hound = BlazeHound()
    for chap in contents:
        hound.parse("%s.trail" % chap)
        if makeHTML:
            out = open("%s.html" % chap,"w")
            out.write(str(sol))
            out.close()
    return hound.root


def genfile(filename, data):
    f = open(filename, "w")
    f.write("######################################\n")
    f.write("### GENERATED FILE! DO NOT CHANGE! ###\n")
    f.write("######################################\n")
    f.write(str(data))
    f.close()


def html():
    index = open("index.html","w")
    print >> index, \
    """
    <html>
    <head>
    <title>webAppWorkshop</title>
    </head>
    <body>

    <h1>webAppWorkshop contents</h1>

    <ul>
    """

    for chap in contents:
##         print >> index, ('<li>[<a href="%s.trail">trail</a>] '
##                          '[<a href="%s.html">%s.html</a>]</li>'
##                          % (chap, chap, chap))
        print >> index, ('<li><a href="%(chap)s.trail">%(chap)s</a></li>'
                         % locals())

    print >> index, \
    """
    </ul>
    </body>
    </html>
    """


if __name__=="__main__":

    import sys
    
    doHTML = "html" in sys.argv
    sol = getSolution(doHTML)

    genfile("nodak.py", sol["nodak"])
    genfile("tests.py", sol["tests"])

    from tests import *
    unittest.main()
