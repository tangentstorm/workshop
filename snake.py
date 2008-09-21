#!/bin/env python2.5
"""
I handle routine task for tangencode projects. 
"""
from path import path
from sys import stdout, argv, exit
import unittest
import sys;
sys.path.insert(0,"code")
sys.path.insert(0,"test") # test first :)


## unit test stuff #########################

def runUnitTest():
    import unittest
    print "-=" * 10 + "+"
    for file in path("test").files("*Test.py"):
        print "%20s: " % file.namebase,
        exec "from %s import %s as tc" % (file.namebase, file.namebase)
        suite = unittest.TestSuite([unittest.makeSuite(tc, "test")])
        DottedTestRunner().run(suite)
    print "-=" * 10 + "+"

class DottedTestResult(unittest._TextTestResult):
    def __init__(self, stream):
        unittest._TextTestResult.__init__(self, stream, 1, 1)

    def addError(self, test, err):
        if err[0] == "skip":
            self.stream.write('s')
        else:
            unittest._TextTestResult.addError(self, test, err)



class DottedTestRunner(unittest.TextTestRunner):
    def __init__(self):
        stream = sys.stdout
        unittest.TextTestRunner.__init__(self, stream)

    def run(self, test):
        result = DottedTestResult(self.stream)
        test(result)
        result.printErrors()
        return result



def runTest(name):
    # new style (literate)
    exec "from spec.%sTest import %sTest; TC=%sTest" \
         % (name, name, name)
    print "%20s: " % name,
    # testXYZ is python standard.. I was using check_...
    suite = unittest.TestSuite([unittest.makeSuite(TC, "check"),
                                unittest.makeSuite(TC, "test")])
    DottedTestRunner().run(suite)







def specfiles():
    """
    I return a list of path objects for spec/*.txt
    """
    return path("spec").files("*.txt")

def spectest():
    """
    I run all the code fragments in spec/*.txt and make sure they work.
    """
    import doctest
    tester = doctest.Tester(globs={}, verbose=0)
    for file in specfiles():
        failed, tried = tester.runstring(file.text(), name=file)
        print ":: %s: %i/%i ok" % (file, tried-failed, tried), 
        if failed:
            print "- %s FAILED" % failed
        else:
            print
    tester.summarize()



def cleanhtml(html):
    """
    I clean up textile's html :)
    """
    # make htmlizer play nice with doctest:
    res = html.replace(
        '<span class="py-src-op">&gt;&gt;</span><span class="py-src-op">&gt;</span>',
        '<span class="py-prompt">&gt;&gt;&gt;</span>')

    # strip out excess lines in the <pre> tags...
    res = res.replace(
        '<span class="py-src-dedent"></span><span class="py-src-endmarker"></span>\n',
        '')
    
    # textile adds these break tags, but I don't like them.
    # if you want them, add them explicitly without the space
    res = res.replace("<br />", "")
    return res 

def wraphtml(html, title):
    """
    I wrap the html that textile produces with a nice template.
    """
    import handy
    return ("\n".join([
        handy.trim(
        '''
        <?xml version="1.0"?
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" 
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html>
        <head>
        <title>%s</title>
        <link rel="stylesheet" href="/stylesheet.css">
        </head>
        <body>
        ''') % title,

        cleanhtml(html),
        
        handy.trim(
        '''
        </body>
        </html>
        ''')]))
        
        
def extract_title(text):
    """
    I find the title (h1.) in a textile file. 
    """
    for line in text.split("\n"):
        line = line.lstrip()
        if line.startswith("h1."):
            return line[3:].strip()

    
def document():
    """
    I generate xhmtml documentation from textile sources in spec/*.txt
    """
    import textile
    if not path("spec").exists():
        print "must have spec to make documents"
        return 
    if not path("docs").exists():
        path("docs").mkdir()
    n = 0
    for spec in specfiles():
        n += 1
        text = spec.text()
        html = textile.textile(text)
        file = open("docs/%s.html" % spec.namebase, "w")
        file.write(wraphtml(html, extract_title(text)))
        file.close()
    print "created %s document(s) in ./docs" % n 
        
if __name__=="__main__":
    if len(argv) < 2:
        print "usage: snake.py command"
        exit()
    else:
        ## lambda stack ##########################
        case = {
            "unittest" : lambda : runUnitTest() ,
            "spectest" : lambda : spectest() ,
            "document" : lambda : document() ,
            "test"     : lambda : [runUnitTest(), spectest()] ,
            "help"     : lambda : [stdout.write("snake commands:\n    "),
                                   stdout.write("\n    ".join(case.keys())),
                                   stdout.write("\n")]}
        action = case.get(argv[1])
        if action:
            action()
        else:
            stdout.write("bad command. try 'snake.py help'\n")
