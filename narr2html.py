"""
trailblazer: convert a narrative python file to html
"""
from handy import xmlEncode, trim
from narrative import testcase
import unittest
import sys

# @TODO: auto-create links based on parsing addMethod() class/method data
# (so you can jump around with <a href="#TheClass.theMethod">xx</a>

# http://effbot.python-hosting.com/file/stuff/sandbox/pythondoc/colorizer.py
try:
    import colorizer
except ImportError:
    colorizer = None

"""
"""

# * types of chunks

class START:
    tag = ""
    end = ""
    @staticmethod
    def format(chunk):
       pass

class TITLE:
    tag = ""
    end = ""
    @staticmethod
    def format(chunk):
        [line] = chunk
        print "<head>"
        print line
        print '<link rel="stylesheet" href="narrative.css"/>'
        print "</head>"
        print "<body>"
        print line.replace("title>", "h1>")

class TEXT:
    tag = ""
    end = ""
    @staticmethod
    def format(chunk):
        for line in chunk:
            print line
        
class CODE:
    tag = "<pre><code>"
    end = "</code></pre>"
    @staticmethod
    def format(chunk):
        if colorizer:
            # pass stdin as fake file object, but...
            hc = colorizer.HtmlColorizer(sys.stdin, sys.stdout)
            # really just use the lines:
            hc.readline = [x+"\n" for x in chunk].__iter__().next
            # disable line numbers:
            hc.lineno = lambda x: None
            # and turn off his pre/code tags:
            hc.begin = lambda : None
            hc.end = lambda : None
            hc.colorize()
        else:
            for line in chunk:
                print xmlEncode(line)

class TEST(CODE):
    tag = "<pre class='test'><code>"


class HEAD:
    tag = ""
    end = ""
    @staticmethod
    def format(chunk):        
        [line] = chunk
        pound, stars, headline = line.split(" ", 2)
        if headline.strip():
            level = len(stars) +1 # h1 is for the title
            print "<h%s>%s</h%s>" % (level, headline, level)
        else:
            # ignore empty headlines (used only for emacs value)
            pass



# * chunk parser
@testcase
def test_getChunks(test):
    chunks = list(getChunks(trim(
        '''
        """
        <title>abc</title>
        """
        import this
        pass
        # * headline 1
        # ** headline 2
        """
        here\'s some text
        more text
        """
        pass
        assert 1 + 2 == 3
        ''')))
    #print [(chunk[0].__name__, chunk[1])  for chunk in chunks]
    modes = [chunk[0].__name__ for chunk in chunks]
    test.assertEquals(
        modes,
        [x.__name__ for x in
         [TITLE,
          CODE, CODE,
          HEAD, HEAD,
          TEXT, TEXT,
          CODE, CODE]])

def toggle(mode):
    # """ always goes into text mode
    # unless we're already in text mode
    if mode is TEXT:
        return CODE
    else: # title, headline, code
        return TEXT

def getChunks(s):
    for mode, lines in getChunksReal(s):
        yield mode, lines

def getChunksReal(s):
    next = CODE
    prev, blankPending = None, None
    chunk = []
    for line in s.split("\n")[:-1]:
        mode = next
        if line.strip() == "":
            # we only want blankPending lines if they're
            # between chunks of code or chunks of text.
            # so blankPending on to blankPending lines
            blankPending = True
            continue
        elif line.startswith('"""'):
            # left-justified python """ strings toggle
            # between code and text mode
            if chunk:
                yield mode, chunk ; chunk = []
            next = toggle(next)
            continue
        elif line.startswith("# *"):
            if chunk:
                yield mode, chunk ; chunk = []
            yield HEAD, [line]
            next = CODE
            blankPending = False
            continue
        elif line.startswith("<title>"):
            if chunk:
                yield mode, chunk ; chunk = []
            yield TITLE, [line]
            continue
        else:
            if blankPending and (mode == prev):
                chunk.append("")
            blankPending = False
            if line.startswith("@") and line.count("testcase"):
                mode = TEST
                next = TEST
            chunk.append(line)
        prev = mode
            

# * main 
def main(filename):
    prev = START
    print "<html>"
    for mode, line in getChunks(open(filename).read()):
        if mode != prev:
            sys.stdout.write(prev.end)
            sys.stdout.write(mode.tag)
        mode.format(line)
        prev = mode
    print "</body>"
    print "</html>"



# * ---
if __name__=="__main__":
    try:
        _, filename = sys.argv
    except:
        print "usage trailblazer.py [-t|xx.py]"
        sys.exit()
    if filename =="-t":
        sys.argv.pop()
        unittest.main()
    else:
        main(filename)

