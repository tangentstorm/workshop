# $Id$
# a simple python source code colorizer

import sys, tokenize, keyword

# TODO: add support for proper rendering of pythondoc comments
# TODO: add support for source code encodings

# this code works under Python 2.2 and later
try:
    enumerate
except NameError:
    def enumerate(seq):
        return [(i, seq[i]) for i in range(len(seq))]

##
# Colorizer base class.

class Colorizer:

    def colorize(self):

        pos = (1, 0)
        cls = None
        tok = None

        source = tokenize.generate_tokens(self.readline)

        self.begin()

        self.lineno(1)
        for type, token, start, end, line in source:
            # FIXME: check source code encoding

            # print >>sys.stderr, tokenize.tok_name[type], repr(token)

            # note: since we're skipping empty tokens, empty lines at
            # the end of the file will be ignored.  to avoid this,
            # change the following test to
            #
            # if type != tokenize.ENDMARKER and (not token or token == "\n"):

            if not token or token == "\n":
                continue

            # assert token != tokenize.NL and token !=tokenize.NEWLINE
            if start != pos:
                self.style(None, None)
                # insert missing whitespace
                if start[0] == pos[0]:
                    self.write(" "*(start[1]-pos[1]))
                else:
                    for i in range(pos[0], start[0]):
                        self.write("\n")
                        self.lineno(i+1)
                    self.write(" "*start[1])

            # figure out what style to use, if any
            if type == tokenize.STRING:
                self.style("string", None)
            elif type == tokenize.NAME:
                if keyword.iskeyword(token):
                    self.style("keyword", token)
                elif tok == "class":
                    self.style("class", token)
                elif tok == "def":
                    self.style("function", token)
                elif tok == "@":
                    self.style("decorator", token)
            elif type == tokenize.COMMENT:
                self.style("comment", None)
            else:
                self.style(None, None)

            # process token parts
            parts = token.split("\n")
            for ix, part in enumerate(parts):
                if not ix:
                    self.write(part)
                elif part or ix < len(parts)-1:
                    cls = self.style(None, None)
                    self.write("\n")
                    self.lineno(start[0]+ix)
                    self.style(cls, None)
                    self.write(part)
            pos = end
            tok = token

        self.style(None, None) # reset style
        self.end()

    ##
    # (hook) Called to render a line number.

    def lineno(self, lineno):
        pass # enter a new line

    ##
    # (hook) Called to read a line from the source.

    def readline(self):
        return sys.stdin.readline()

    ##
    # (hook) Called to write a line of text to the target.

    def write(self, text):
        sys.stdout.write(text)

    ##
    # (hook) Called to change to a new style.
    #
    # @param style The requested style.  The value None means "plain
    #   text".  Other style values are "class", "comment", "function",
    #   "decorator", "keyword", and "string".
    # @param token The actual token that caused the colorizer to
    #   request this style.  This is only set for "class", "function",
    #   "decorator", and "keyword" styles; for other styles, this
    #   parameter is None.
    # @return The old style (before this call was made).

    def style(self, style, token):
        pass

    ##
    # (hook) Called before colorization starts.

    def begin(self):
        pass

    ##
    # (hook) Called after colorization ends.  The style is set to None
    # before this method is called.

    def end(self):
        pass

##
# A colorizer that reads from, and writes to file streams.

class FileColorizer(Colorizer):

    def __init__(self, infile, outfile):

        if not hasattr(infile, "read"):
            infile = open(infile)

        def readline():
            s = infile.readline()
            return s and s.expandtabs().rstrip() + "\n"
        self.readline = readline

        if not hasattr(outfile, "write"):
            outfile = open(outfile, "w")
        self.write = outfile.write

##
# A colorizer that reads from a file (or a stream), and renders output
# as HTML.

class HtmlColorizer(FileColorizer):

    cls = None

    def __init__(self, infile, outfile):

        FileColorizer.__init__(self, infile, outfile)

        # replace write with an escaping
        import cgi
        self.write_raw = self.write
        def write(text):
            # FIXME: use encode(xmlcharrefreplace) as well ?
            self.write_raw(cgi.escape(text))
        self.write = write

    def style(self, cls, token):
        current = self.cls
        if cls == self.cls:
            return current
        if self.cls:
            self.write_raw("</span>")
        if cls:
            self.write_raw("<span class='%s'>" % cls)
        self.cls = cls
        return current

    def begin(self):
        self.write_raw("<pre class='python'><code>")

    def end(self):
        self.write_raw("</code></pre>")

    def lineno(self, line):
        self.write_raw(
            "<span id='line%s' class='lineno'>%05d</span> " % (line, line)
            )

if __name__ == "__main__":
    # sanity check
    PYTHONWORKS_STYLE = """
    .class {color:firebrick;font-weight:bold;}
    .comment {color:darkolivegreen;font-style:italic;}
    .decorator {color:firebrick;}
    .function {color:firebrick;font-weight:bold;}
    .keyword {color:firebrick;}
    .lineno {color:gray;border-right:1px solid gray;padding-right:5px;}
    .string {color:navy;}
    """
    TRAC_STYLE = """
    .class {color:#900;font-weight:bold;border-bottom:none;}
    .comment {color:#998;font-style:italic;}
    .decorator {color:#900;border-bottom:none;}
    .function {color:#900;font-weight:bold;border-bottom:none;}
    .keyword {color:#000;font-weight:bold;}
    .lineno {color:black;}
    .string {color:#b84;font-weight:bold;}
    }
    """
    try:
        file = sys.argv[1]
    except IndexError:
        file = "pythondoc.py"
    print "<html><head>"
    print "<style>", PYTHONWORKS_STYLE, "</style>"
    print "</head><body>"
    c = HtmlColorizer(file, sys.stdout)
    import time
    t0 = time.clock()
    c.colorize()
    t0 = time.clock() - t0
    print "</body></html>"
    print >>sys.stderr, t0
