"""
zebra: a text generation and reporting system
"""
import os
import string
import xml.sax
import unittest
import handy
from handy import deNone
from handy import xmlEncode
import html

# * tags
'''
* tags

** group name="basics"
*** item tag="exec"
*** item tag="include"
*** item tag="show"
*** item tag="insert"
*** item tag="skin"
*** item tag="stripe"
*** item tag="wrap"
*** item tag="zebra"

** group name="code generation"
*** item tag="ef"
*** item tag="el"
*** item tag="group"
*** item tag="if"
*** item tag="report"

** group name="prenamed"
*** item tag="content"
*** item tag="description"
*** item tag="keywords"
*** item tag="title"

** group name="scripting"
*** item tag="eval"

** group name="substripes"
*** item tag="body"
*** item tag="head"
*** item tag="none"
*** item tag="tail"

** split

** tag name="body"
*** desc
The innermost part of a @@report@@ or @@group@@.
The body stripe is repeated for each 
record in the results.
*** example
\* report
\** query source="myDB"
select item from table
\** body
&lt;li&gt;{item}
** tag name="content"
*** desc
This is a prenamed stripe for use by content authors.
It simply marks its children as being the actual content
of a page.
*** example
\* title
A story.
\* content
Once upon a time, something happened. The end.
** tag name="description"
*** desc
A prenamed stripe that marks its children as being
the description of a page (to be inserted into an HTML META
tag, for example)
*** example
\* title
A story
\* description
A humorous tale of love, adventure, and danger.
\* content
Once upon a time, something happened. The end.
** tag name="ef"
*** desc
A logic tag that implements an "else if".
Must follow an @@if@@.
*** example
\* if native="$x > 50"
Too low.
\* ef native="$x < 50"
Too high.
\* el native="$x = 50"
Just right!
*** attr name="native" desc="Allows for testing in the native language. Disallowed in safe mode."
*** attr name="test" desc="A test in ZebraScript. Will be translated to the native language. (not yet implemented)"
** tag name="el"
*** desc
A logic tag that implements "else". Must follow @@if@@ or @@ef@@.
See @@ef@@ for example.
*** attr name="native" desc="Allows for testing in the native language. Disallowed in safe mode."
*** attr name="test" desc="A test in ZebraScript. Will be translated to the native language. (not yet implemented)"
** tag name="eval"
*** desc
Indicates that the enclosed data is to be treated as 
(python) code to be evaluated at compile time by  
<br>&nbsp;<br>
The eval tag may be used to build stripes on the fly.
Simply populate a variable called STRIPE. If STRIPE
is set to anything other than None when the code
is finished evaluating, then a STRIPE will be inserted
into the current context. 
<br>&nbsp;<br>
At some point, this tag will be used to make zebra documents
scriptable. For now it should not be used to modify the zebra document
that is being parsed, because the interface to the zebra parser will
probably change.
<br>&nbsp;<br>
<b>Note:</b> eval may not contain any other stripes, nor
will interpolation of {$variables}, {fields}, and {!stripes} 
work within an eval.
*** example
\* zebra
\** eval
# python stuff
STRIPE = "Four plus four is " + `4+4`
** tag name="exec"
*** desc
Indicates that the enclosed stripes are to be treated as executable
code to be run by the web server. For example, when making a 
PHP3 application, the PHP3 should go here.
*** example
\* zebra
This gets shown.
\** exec
print "And so does this"; # assuming PHP3, perl, etc..
** tag name="group"
*** desc
Group implements headers and footers in a @@report@@.
May be nested inside another group.
Its "head" is shown whenever the content of the current record's
grouping field is different from that of the previous
record. Its "tail" is shown whenever the content of the current record's
grouping field is different from that of the next record.
See @@report@@ for an example.
*** attr name="field" desc="The field on which to group."
** tag name="head"
*** desc
A header. The part of a @@skin@@, @@report@@, or @@group@@ tag that
gets shown before the contents of the stripe.
** tag name="if"
*** desc
A logic tag that implements an "if". May be used with @@ef@@ and
@@el@@ to produce complex conditional logic. May be nested.
*** example
X is definitely 
\* if test="not {xIsTrue}"
NOT
\* show
true.
*** attr name="native" desc="Allows for testing in the native language. Disallowed in safe mode."
*** attr name="test" desc="A test in ZebraScript. Will be translated to the native language. (not yet implemented)"
** tag name="include"
*** desc
Include one zebra file within another.
*** example
\* include file="bubba.zi"
*** attr name="file" desc="the name of the file to be included. Conventionally, *.zi"
** tag name="insert"
*** desc
Inserts a named stripe. Empty tag, so it requires a "/".
May (and should) be abbreviated with {!stripename}
*** example
\* zebra
\** stripe name="fred"
This is fred
\** show
Here's fred:
\*** insert stripe="fred" /
Here's fred again: {!fred}
*** attr name="stripe" desc="the name of the stripe"
** tag name="keywords"
*** desc
A prenamed stripe to contain keywords for describing a document. Used, for example,
to populate the "description" META tag in HTML.
*** example
\* title
A story.
\* keywords
adventure, story, stories, plot
\* content
Once upon a time, something happened. The end.
** tag name="none"
*** desc
In a @@report@@, this stripe is displayed if the @@query@@ returns no records.
*** example
\* report
\** query
select something from table where (1=2)
\** head
This won\'t ever get shown.
\** body
Neither will this.
\** none
Nothing shown because 1 never equals 2.
** tag name="report"
*** desc
The report tag generates code to format the results of a @@query@@. 
*** example
\* zebra
\** report
\*** query source="myDB"
select person, department from employees order by department
\*** group field="department"
\**** head
People in the {department} department:
&lt;ul&gt;
\**** body
&lt;li&gt;{person}
\**** tail
&lt;/ul&gt;
*** attr name="query" desc="a (predefined) query to use (optional, not yet implemented)"
** tag name="show"
*** desc
Indicates that the enclosed data is meant to be shown to
the web browser. Often translates into a "print" statement,
depending on the language. Mostly used to avoid a "* /"
for @@exec@@ or @@eval@@, since zebra is in "show" context
by default.
*** example
\* zebra
in show context
\** exec
print "in exec context";
\** show
back in show context.
** tag name="skin"
*** desc
Defines a skin for wrapping stripes.
*** example
\* skin name="brackets"
\** head
[[[[[[
\** tail
]]]]]]]
\* wrap skin="brackets"
This will be in brackets.
*** attr name="name" desc="the name of the skin"
** tag name="stripe"
*** desc
A mechanism for naming stripes.
*** example
\* zebra
\** stripe name="fred"
This is the stripe called "Fred".
\** show
Here\'s fred: {!fred}
*** attr name="name" desc="the name of the stripe"
** tag name="tail"
*** desc
A footer. The part of a @@skin@@, @@report@@, or @@group@@ tag that
gets shown after the contents of the stripe.
** tag name="title"
*** desc
A prenamed stripe to contain title of a document. Used, for example,
to populate the TITLE tag in HTML.
*** example
\* title
A story.
\* keywords
adventure, story, stories, plot
\* content
Once upon a time, something happened. The end.
** tag name="wrap"
*** desc
Wraps the enclosed stripe in a skin. See @@skin@@ for example.
*** attr name="skin" desc="the name of the skin to use"
** tag name="zebra"
*** desc
Top level tag. Indicates that this is a Zebra file.
*** example
\* zebra
hello, world!
'''
# * tags2html utility
"""
this isn't really part of zebra. it's just a tool for
generating the docs. I'm not even sure it works. :/
"""
def makedocs():
    import xmllib # deprecated!

class tagdoc(xmllib.XMLParser):

    def __init__(self):
        xmllib.XMLParser.__init__(self)
        self.STRIPE = "" # used to cache data between tags

    ## main menu at the top:

    def start_group(self, attrs):
        print("<h3>" + attrs["name"] + "</h3>\n<ul>")

    def end_group(self):
        print("</ul>")

    def start_item(self, attrs):
        print('<li><a href="#%s">%s</a>' % (attrs["tag"], attrs["tag"]))


        ## individual tags
    def start_tag(self, attrs):
        print('<h2><a name="%s">%s</a></h2>' % (attrs["name"], attrs["name"]))
        self.attriblist = []

    def end_tag(self):
        if len(self.attriblist) > 0:
            print(
                """<table width="70%" border="1"><tr><th align="left">attribute</th><th align="left">meaning</th></tr>""")
            for a in self.attriblist:
                print("<tr><td>%s</td><td>%s</td></tr>" % (a["name"], a["desc"]))
            print("</table>")

    def start_desc(self, attrs):
        self.STRIPE = ""
        print('<p class="desc">')

    def end_desc(self):
        print(self.STRIPE)
        print('</p>')

    def start_example(self, attrs):
        self.STRIPE = ""
        print('<pre class="example">')

    def end_example(self):
        print(self.STRIPE)
        print('</pre>')

    def start_attr(self, attrs):
        self.attriblist.append(attrs)

    def start_split(self, attrs):
        print("<hr>")

        ## char data
    def replaceAts(self, match):
        tag = match.group(1)
        return '<a href="#%s">&lt;%s&gt;</a>' % (tag, tag)

    def handle_data(self, data):
        reAt = re.compile("\@\@([^@]+)\@\@", re.I | re.S )
        res = reAt.sub(self.replaceAts,data)
        self.STRIPE = self.STRIPE + res

    print("""
    <html>
    <head>
    <title>Zebra Tag Reference</title>
    <style type="text/css">
    body, p, td, th {
      background: white;
      font-family: verdana, arial
      font-size: 10pt;
    }

    .desc, .example, table {
      margin-left: 25px;
      margin-right: 50px;
    }

    th { color: white; background: black }
    td { color: black; background: #ccccff }

    pre.example {
      background: gold;
    }
    </style>
    </head>
    <body>
    <h1>Zebra Tag Reference</h1>
    <p><b>last updated:</b> %s <br>
    Zebra is in flux at the moment, so the documentation may
    be slightly ahead of or behind the current code. They
    should sync up around release 1.0.
    </p>
    <a href="../">back to main zebra page</a>
    """ % time.asctime(time.localtime(time.time())))

    docs = tagdoc()
    docs.feed(o2x.o2x(open("tags.out").read()))

    print("""
    <hr>
    &copy; 1999 Zike Interactive.... <a href="../">back to main zebra page</a>
    </body>
    </html>
    """)


# * lexer for expressions:
# ** test
class LexerTestCase(unittest.TestCase):

    def test_simpleLex(self):
        goal = [("NAME", "x")]
        actual = lex("x")
        assert actual == goal, \
               "didn't parse single var correctly:\n%s" % str(actual)


    def test_lambda(self):
        """we don't want to allow lambdas!"""
        try:
            print(lexer_parse("lambda x: 4+x"))
        except SyntaxError:
            pass
        else:
            self.fail("lambdas should raise a syntax error!")


# ** types
INT, STR, TUP = type(0), type(""), type(())
# ** _walk
def _walk(tree, res):
    """routine to walk the parse tree"""
    for node in tree:
        TYP = type(node)
        if TYP==INT:
            try:
                import token
                res.append(token.tok_name[node])
            except KeyError:
                pass
        elif TYP==STR:
            res.append(node)
        elif TYP==TUP:
            _walk(node, res)
# ** lex
def lex(expression):
    """Tokenize the expression by flattening python's own parse tree."""
    #@TODO: the tokenize module already does this..
    import parser, symbol
    tree = parser.expr(expression).totuple()
    toks = []
    _walk(tree,toks)

    res = []
    for _ in range(0,len(toks),2):
        res.append(tuple(toks[_:_+2]))

    ## we don't need this junk at the end:
    if res[-2:] == [('NEWLINE',''), ('ENDMARKER', '')]:
        res = res[:-2]

    return res

# ** validate
def validate(tokens):
    """Validation of zebra tokens."""

    for token in tokens:
        #>> lambda <<#
        # make sure they don't have lambdas, because we can't
        # easily translate them to other languages.
        if token[0]=="NAME" and token[1]=="lambda":
            raise SyntaxError("lambdas are not allowed in zebra expressions")
    return tokens
# ** parse
def lexer_parse(expression):
    """conveniece function to lex and validate an expression"""
    return validate(lex(expression))

# * Z2X : zbr 2 xml
# ** test
class Zbr2xmlTestCase(unittest.TestCase):

    def test_indent(self):

        ## the blank line before the * checks for a
        ## whitespace error!
        zbr = trim(
            """
            This is normal text.
            * if 1==2:
                This should never show up.
            * el:
            This line isn't part of the else.
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            This is normal text.<nl/>
            <if condition="1==2">
            This should never show up.<nl/>
            </if>
            <el>
            </el>
            This line isn't part of the else.<nl/>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't indent correctly:\n%s" % actual



    def test_xmlchars(self):
        zbr = trim(
            """
            <P>Hello&nbsp;World!!! ><
            """)
        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            &lt;P&gt;Hello&amp;nbsp;World!!! &gt;&lt;<nl/>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't cope with xmlchars correctly:\n%s" % actual


    def test_var(self):
        zbr = trim(
            """
            {
            My name is {?name?}.
            }
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            {<nl/>
            My name is <var>name</var>.<nl/>
            }<nl/>
            </zebra>
            """)
        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't cope well with {?vars?}:\n%s" % actual



    def test_expr(self):
        zbr = trim(
            """
            I will be {:age + 4:} next year.
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            I will be <xpr>age + 4</xpr> next year.<nl/>
            </zebra>
            """)
        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't cope well with {:exprs:}:\n%s" % actual

    def test_exec(self):
        zbr = trim(
            """
            * exec:
                name = 'fred'
                xml = '<xml>woohoo!</xml>'
                dict = {}
                dict['a'] = 'b'

                hope(there_was_no_nl_tag_there)
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <exec>
            name = 'fred'
            xml = '&lt;xml&gt;woohoo!&lt;/xml&gt;'
            dict = {}
            dict['a'] = 'b'

            hope(there_was_no_nl_tag_there)
            </exec>
            </zebra>
            """)
        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't cope well with exec:\n%s" % actual



    def test_invalid(self):
        """check invalid tags"""
        zbr = trim(
            """
            * thisIsAnInvalidTag
            """)
        try:
            Z2X().translate(zbr)
        except:
            gotError = 1
        else:
            gotError = 0

        assert gotError, \
               "Didn't get error on invalid tag."


    def test_comment(self):
        zbr = trim(
            """
            *# this is a comment
            this isn't
            *     # this is
            """)
        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <rem>this is a comment</rem>
            this isn't<nl/>
            <rem>this is</rem>
            </zebra>
            """)
        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't handle comments right:\n%s" % actual



    def test_include(self):
        #@TODO: drop trailing : from include syntax
        zbr = trim(
            """
            * include includefile:
            """)

        #@TODO: it should realy be <include file="includefile"/>
        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <include file="includefile">
            </include>
            </zebra>
            """)
        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "doesn't handle includes right:\n%s" % actual



    def test_forNone(self):
        zbr = trim(
            """
            * for people:
                {?name?} is a nice person.
            * none:
                No people here!
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="people">
            <var>name</var> is a nice person.<nl/>
            </for>
            <none>
            No people here!<nl/>
            </none>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "Doesn't do for..none right:\n%s" % actual


    def test_forHeadBodyFoot(self):
        zbr = trim(
            """
            * for people:
                * head:
                    PEOPLE
                    -------
                * body:
                    {?name?} is a nice person.
                * foot:
                    -------
                    THE END
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="people">
            <head>
            PEOPLE<nl/>
            -------<nl/>
            </head>
            <body>
            <var>name</var> is a nice person.<nl/>
            </body>
            <foot>
            -------<nl/>
            THE END<nl/>
            </foot>
            </for>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "Doesn't do for/head/body/foot right:\n%s" % actual


    def test_notBlocks(self):
        zbr = trim(
            """
            * if x==1:
                * include page_one;
            * ef x==2:
                * include page_two;
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <if condition="x==1">
            <include file="page_one"/>
            </if>
            <ef condition="x==2">
            <include file="page_two"/>
            </ef>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "Doesn't handle ; blocks right:\n%s" % actual

    def test_newline(self):
        zbr = trim(
            """
            hello, world!

            this test is good \\
            if there is no break here
            i want a newline after this<tag/>
            the end
            """)

        goal = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            hello, world!<nl/>
            <nl/>
            this test is good if there is no break here<nl/>
            i want a newline after this&lt;tag/&gt;<nl/>
            the end<nl/>
            </zebra>
            """)

        actual = Z2X().translate(zbr)
        assert actual==goal, \
               "zbr2xml doesn't handle newlines correctly:\n%s" % actual
# ** code
"""
translate zebra's *.zbr files to xml
"""
class Z2X:
    """Class to translate zebra report files (*.zbr) to xml"""

    ## public interface ############################

    def translate(self, zbr):
        """Z2X().translate(zbr) => xml representation of the report"""

        ## we deal with the file line by line:
        lines = string.split(zbr, "\n")

        ## strip empty string that shows up if \n on last line:
        if lines[-1]=='': lines = lines[:-1]

        ## master template:
        res = '<?xml version="1.0"?>\n'
        res = res + self._deBlock(lines,"zebra")
        return res


    ## helper method ###############################

    def _deBlock(self, lines, tag, attrs="", left=0):
        """Recursive routine to handle chunks of ZBR code"""

        if attrs:
            res = "<%s %s>\n" % (tag, attrs)
        else:
            res = "<%s>\n" % tag

        x = 0
        while x < len(lines):
            lineNo = x + 1

            ## only look from the leftmost position onwards.
        ## (it's okay because we make sure theres' nothing
            ## but space in there a little later..
            line = lines[x][left:]

            ## comments are single lines starting with * #
            if string.lstrip(string.lstrip(line[1:])).startswith("#"):
                # this little mess just strips off the * and #
                res = res + "<rem>%s</rem>\n" \
                      % xmlEncode(string.lstrip(line[1:])[2:])

            ## zebra commands begin with *
            elif string.lstrip(line).startswith("*"):
                line = string.strip(line)

                ## .. and end with : or ;
                if line[-1] == ":":
                    isBlock = 1
                elif line[-1] == ";":
                    isBlock = 0
                else:
                    raise SyntaxError("* tag without ':' or ';' on line %i\n[%s]" % (lineNo, line))
                line = line[:-1]

                ## get the tokens after *:
                toks = string.split(line, " ")[1:]
                tok = toks[0]

                ## see if we can parse that token:
                if hasattr(self, "parse_"+tok):
                    attrs = getattr(self,"parse_"+tok)(toks)
                else:
                    raise NameError("Don't know how to handle '%s' on line %i" % (line, lineNo))

                ## find the new left edge:
                if isBlock:
                    newleft = 0
                    topx = x = x + 1
                    if topx >= len(lines):
                        newleft = left - 1
                    else:
                        for i in range(len(lines[topx])):
                            if lines[topx][i]!=" ":
                                newleft = i
                                break

                    ## find the end of the block, which should be
                    ## less indented than the inside of the block.
                    if newleft <= left:
                        ## the block is empty
                        pass
                    else:
                        while x<len(lines):
                            if (lines[x].strip()=="") or (lines[x][:newleft])==(" " * newleft):
                                x += 1
                            else:
                                break

                    ## run this routine recursively on the inner block:
                    res = res + self._deBlock(lines[topx:x],
                                              tok, attrs, newleft)

                    ## we've already added 1, so jump back to the top:
                    continue


                else:
                    # not a block...
                    res = res + "<%s %s/>\n" % (tok, attrs)


            ## just a normal line..
            else:
               if tag == "exec":
                    end = "\n"
               elif (line.endswith(chr(92))):
                    line = line[:-1]
                    end = ""
               else:
                    end = "<nl/>\n"
               res = res + deCurl(xmlEncode(line)) + end
            ## move on to the next line and continue with the while() loop:
            x = x + 1

        ## cap off the current tag and get out of here!
        res = res + "</%s>\n" % tag
        return res


    ## tag handlers #######################################

    def parse_exec(self, tokens):
        return '' # exec has no options (yet)

    def parse_if(self, tokens):
        return 'condition="%s"' % " ".join(tokens[1:])

    def parse_ef(self, tokens):
        return 'condition="%s"' % " ".join(tokens[1:])

    def parse_el(self, tokens):
        return '' # el has no options (yet)

    def parse_for(self, tokens):
        return 'series="%s"' % tokens[1]

    def parse_none(self, tokens):
        return '' # none has no options

    def parse_head(self, tokens):
        return '' # no options yet

    def parse_body(self, tokens):
        return '' # no options yet

    def parse_foot(self, tokens):
        return '' # no options yet

    def parse_glue(self, tokens):
        return '' # no options yet

    def parse_include(self, tokens):
        return 'file="%s"' % tokens[1]

# * helpers
# ** entitymap
_entitymap = {
    "<" : "lt",
    ">" : "gt" ,
    "&" : "amp",
    }
# ** xmlencode
def xmlEncode(s):
    """Converts <, >, and & to xml entities."""
    res = ""
    for ch in s:
        if _entitymap.has_key(ch):
            res = res + "&" + _entitymap[ch] + ";"
        else:
            res = res + ch
    return res
# ** decurl ??
def deCurl(s):
    """
    {abc} => <var>abc</var>
    {:xyz:} => <expr>xyz</expr>

    use backslash to escape.
    eg, \{abc}
    or {: 'this is a \:} string' :}
    """
    import re
    # these don't match newlines cuz there's no re.DOTALL.
    # that's because vars/exprs are single lines only!
    # which is helpful if you've got {'s in your template
    # eg, with javascript on an html page..
    reVar = re.compile(r'(?!\\){\?(.*?)\?}')
    reExpr = re.compile(r'(?!\\){:(.*?)(?!\\):}')
    res = s
    # do xpr first so we don't have to complicate reVar to look for :'s
    res = reExpr.sub('<xpr>\\1</xpr>', res)
    res = reVar.sub('<var>\\1</var>', res)
    return res

# * X2M : our top level xml parser
# ** idea
"""
The basic idea here was that the zebra compiler uses
the same type of data structure as zebra itself. So
in theory, you could use a template to produce different
backends.
"""
# ** test
class Xml2mdlTestCase(unittest.TestCase):

    def setUp(self):
        self.data = trim(
            """
            <?xml version="1.0"?>
            <top>
              <person name="Michal">
              <skill>Python</skill>
              <skill>ASP</skill>
              </person>
            </top>
            """)

    def test_X2mParser(self):
        x2m = X2M()

        assert x2m.model == [], \
               "Doesn't initialize model."

        # now test for the correct model:
        goal = [{'__tag__': u'top',
                 '__data__':
                 [u'\n', u'  ',
                  {'__tag__': u'person',
                   '__data__':
                   [u'\n', u'  ',
                    {'__tag__':
                     u'skill', '__data__':
                     [u'Python']},
                    u'\n', u'  ',
                    {'__tag__': u'skill',
                     '__data__': [u'ASP']},
                    u'\n', u'  '],
                   u'name': u'Michal'},
                  u'\n']}]

        actual = x2m.translate(self.data)
        self.assertEquals(actual,goal)

# ** code
"""
code to convert xml to a model usable by zebra reports.
"""
class X2M(xml.sax.handler.ContentHandler):
    """I parse XML into zebra-style models."""

    def __init__(self):
        self.model = []
        self.model_point = self.model
        self.point_stack = self.model

    def translate(self, xml_string):
        """X2M().translate(xml) => a model of the xml data."""
        xml.sax.parseString(xml_string, self)
        return self.model


    def startElement(self, tag, attributes):
        """Add a dict describing the tag to the model, then add it to stack."""
        dict = {"__tag__": tag, "__data__":[]}
        dict.update(attributes)

        self.model_point.append(dict)
        self.point_stack.append(self.model_point)
        self.model_point=dict["__data__"]

    def endElement(self, tag):
        """Pop the point off the point stack."""
        self.model_point = self.point_stack.pop()

    def characters(self, data):
        self.model_point.append(data)

    def ignorableWhitespace(self, data):
        self.model_point.append(data)


# * Bootstrap
# ** test
class BootstrapTestCase(unittest.TestCase):

    def test_basics(self):
        zbx = trim(
            """
            <zebra>
            <rem> ignore me! </rem>
            hello, world!
            </zebra>
            """)

        rpt = Bootstrap().toObject(zbx)

        for item in ("fetch", "show"):
            assert hasattr(rpt, item), \
               "Report objects don't have .%s()!" % item

        actual = rpt.fetch()
        assert actual == "hello, world!", \
               "basic 'hello, world' doesn't work:\n%s" % actual

        assert actual == rpt.fetch(), \
               "calling fetch() a second time yields different results. :/"


    def test_for(self):

        model = {
            "a":"alaska",
            "stuff":[
                {"a":"apple", "b":"banana", "c":"cherry"},
                {"a":"aardvark", "b":"bull weevil", "c":"catepillar"},
                {"a":"alice", "b":"betty", "c":"carol"},
                ],
            }

        zbx = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <rem>test scope</rem>
            <xpr>a</xpr><nl/>
            <for series="stuff">
            <xpr>a</xpr>, <xpr>b</xpr>, <xpr>c</xpr>
            <nl/>
            </for>
            <xpr>a</xpr><nl/>
            </zebra>
            """)

        goal = trim(
            """
            alaska
            apple, banana, cherry
            aardvark, bull weevil, catepillar
            alice, betty, carol
            alaska
            """)

        actual = Bootstrap().toObject(zbx).fetch(model)
        assert actual == goal, \
               "for() loops don't work:\n---\n%s---" % actual


    def test_conditionals(self):
        model = {
            "names": [
            {"name":"a"},
            {"name":"b"},
            {"name":"c"}]
            }

        zbx = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="names">
            <if condition="name=='a'">Argentina</if>
            <ef condition="name=='b'">Bolivia</ef>
            <el>Chile</el>
            <glue>, </glue>
            </for>
            </zebra>
            """)
        goal = "Argentina, Bolivia, Chile"


        actual = Bootstrap().toObject(zbx).fetch(model)
        assert actual== goal, \
               "if/el/ef don't work:\n---%s---" % actual



    def test_none(self):
        model = {"emptylist": [],
                 "fulllist": [{"a":"b"}]}
        zbx = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="emptylist">
            THIS SHOULD NOT SHOW UP
            </for>
            <none>
            Nothin's empty. 
            </none>
            <for series="fulllist">
            Somethin's full.
            </for>
            <none>
            THIS SHOULD NOT SHOW UP
            </none>
            </zebra>
            """)

        goal = "Nothin's empty. Somethin's full."

        actual = Bootstrap().toObject(zbx).fetch(model)
        assert actual == goal, \
               "none doesn't work:\n%s" % actual


    def test_xpr(self):
        zbx = "<zebra><xpr> (1 + 1) * 5 - 8 </xpr></zebra>"
        goal = "2"
        actual = Bootstrap().toObject(zbx).fetch()
        assert actual == goal, \
               "expressions don't work:\n%s" % actual

    def test_whitespace(self):
        zbx = trim(
            """
            <zebra>
            <xpr>5</xpr> <xpr>2</xpr><nl/>
            </zebra>
            """)
        goal = "5 2\n"
        actual = Bootstrap().toObject(zbx).fetch()
        assert actual == goal, \
               "whitespace is screwed up:\n%s" % actual

    def test_exec(self):
        # note: the <>'s mean something!
        zbx = trim(
            """
            <zebra>
            <exec>
            ex = '&lt;executive'            
            ex += ' decision&gt;'
            </exec>
            <xpr>ex</xpr>
            </zebra>
            """)

        goal = "<executive decision>"

        actual = Bootstrap().toObject(zbx).fetch()
        assert actual == goal, \
               "expressions don't work:\n%s" % actual



    def test_headFootSimple(self):

        # check the simple case, not the grouped version.

        model = {
            "list": [
            {"toy":"ball"},
            {"toy":"yoyo"},
            ]}

        zbx = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="list">
            <head>Some toys: [</head>
            <var>toy</var>
            <glue>, </glue>
            <foot>]</foot>
            </for>
            </zebra>
            """)

        goal = "Some toys: [ball, yoyo]"

##         print '--------'
##         print Bootstrap().compile(zbx)
##         print '--------'

        actual = Bootstrap().toObject(zbx).fetch(model)
        assert actual == goal, \
               "head/tails don't work:\n%s" % actual

    def test_nested_for(self):
        model = {"all": [{"subs":[{"value":"a"}]},
                         {"subs":[{"value":"b"}]}]}
        zbx = trim(
            """
            <?xml version="1.0"?>
            <zebra>
            <for series="all">
            <head>[</head>
            <for series="subs">
            <head>{</head>
            <var>value</var>
            <foot>}</foot>
            </for>
            <foot>]</foot>
            </for>
            </zebra>
            """)
        goal = "[{a}{b}]"
        actual = Bootstrap().toObject(zbx).fetch(model)
        self.assertEquals(actual, goal)



    def test_include(self):
        import tempfile
        tf = tempfile.NamedTemporaryFile(suffix=".zb")
        zbx = trim(
            """
            <zebra>
            <include file="%s">
            </include>
            </zebra>
            """ % tf.name)

        goal = "This is the include file!\n"
        tf.write(goal) ; tf.flush()

        actual = Bootstrap().toObject(zbx).fetch()
        tf.close()
        assert actual == goal, \
               "includes don't work:\n%s" % actual

    def test_brackets(self):
        zbx = '<zebra><xpr> ("a","b","c")[1] </xpr></zebra>'
        goal = "b"
        actual = Bootstrap().toObject(zbx).fetch()
        assert actual == goal, \
               "brackets cause problems:\n%s" % actual

    def test_body(self):
        zbx = '<zebra><body>blah</body></zebra>'
        goal = "blah"
        actual = Bootstrap().toObject(zbx).fetch()
        assert actual == goal, \
               "<body> doesn't work:\n%s" % actual

# ** code
"""
Bootstrap compiler for 
"""
class Bootstrap:
    """A class to compile zebra reports until zebra can compile itself."""

    def __init__(self):
        self.counter = {}
        self.loopvars = []
        self.lastLoopvar = None

    def gensym(self, prefix):
        """
        Return a unique symbol for variable names in generated code.
        """
        self.counter.setdefault(prefix,0)
        sym = "%s%i" % (prefix, self.counter[prefix])
        self.counter[prefix] += 1
        return sym


    parserClass = X2M

    def toObject(self, zbx):
        """bstrap.toObject(zbx) => a python Report object"""
        exec(self.compile(zbx))
        return Report()


    def parse(self, zbx):
        """Returns a Model-style representation of zbx"""
        parser = self.parserClass()
        parser.translate(zbx)
        return parser.model


    def compile(self, zbx):
        """Bootstrap.().compile(zbx) => python code for zbx"""

        return self.walk(self.parse(zbx))


    def walk(self, model, mode="show"):
        """Walks along the model, converting it to code..."""
        import types

        res = ""

        for item in model:
            ## XML tags are represented as dicts
            if type(item) == dict:

                ## do we have a handler for the tag?
                if not hasattr(self, "handle_" + item["__tag__"]):
                    raise NameError("Don't know how to handle <%s>" % item["__tag__"])

                res += getattr(self, "handle_" + item["__tag__"])(item["__data__"], item)


            ## CDATA is represented as strings
            elif type(item) == str:

                if mode=="show":
                    ## strip first and last newlines, if present
                    ## @TODO: why do I do this?
                    if item and item[0]=="\n": item = item[1:]
                    if item and item[-1]=="\n": item = item[:-1]
                    if item:
                        res = res + "zres = zres + '%s'\n" \
                              % escape(item)
                else: # exec mode:
                    res = res + item

            else:
                raise TypeError("Don't know how to cope with %s" % type(item))

        return res


## @TODO: probably get rid of this..
## though, it might come in handy if trying to get zebra to work with
## a really strict language... (but why do that?)

##     ## language-specific templates for handling scope ##############

##     def scopify(self, expression):
##         "points names in expressions to the current scope"
##         import string, keyword
##         res = []
##         toks = lexer_parse(string.strip(expression))
##         for token in toks:
##             if token[0]=="NAME" and not keyword.iskeyword(token[1]):
##                 res.append("scope.get('%s','')" % token[1])
##             else:
##                 res.append(token[1])
##         return string.join(res, " ")



    ## individual tag templates ####################################

    def handle_zebra(self, model, attrs):
        res = trim(
            """
            class Report:
            
                def show(self, model={}):
                    print self.fetch(model)

                def fetch(self, model={}):
                    import copy   # used for pushing scope onto stack

                    scope = globals()
                    # This scope thing is so that we can generate
                    # code that says:
                    #
                    #         zres = zres + x
                    # *OR*
                    #         zres = zres + scope.get(x, '')
                    #
                    # It also actually does variable scoping,
                    # when combined with scope_stack, below.
                    #
                    # I wanted to use scope=locals(), but
                    # then the 'zres + x' wouldn't work.
                    # @TODO: is this scope scheme threadsafe?
                    
                    scope_stack = []

                    # scope.update(model), but model might be a UserDict:
                    for item in model.keys():
                        scope[item] = model[item]

                    # zres is the result (the output we're building)
                    zres = ""
            """)
        res = res + indent(self.walk(model), 2)
        res = res + trim(
            ''' 
            # end of Report.fetch()
                    return zres

            def fetch(model={}):
                return Report().fetch(model)
                
            def show(model={}):
                return Report().show(model)
            ''')
        return res

    def handle_rem(self, model, attrs):
        return "" # @TODO: do we want comments after compliation?


    def handle_for(self, model, attrs):
        loopvar = self.gensym("loopvar")
        self.loopvars.append(loopvar)
        data = {"loopvar":loopvar}
        data.update(attrs)
        res = trim(
            '''
            _%(loopvar)s_max_ = len(scope["%(series)s"])
            for %(loopvar)s in range(_%(loopvar)s_max_):
                # handle scope inside the loop in case we have
                # recursive names (eg, children->children->children)
                scope_stack.append(copy.copy(scope))
                
                # can't do .update if it's a UserDict:
                mdl = scope["%(series)s"][%(loopvar)s]
                for item in mdl.keys():
                    scope[item]=mdl[item]
            ''' % data)
        res = res + indent(self.walk(model), 1)
        res = res + trim(
            '''
            #   ## close for-%(series)s loop ##########
                globals().update(scope_stack.pop())
            ''' % attrs)
        self.lastLoopvar = self.loopvars.pop()
        return res

    def handle_none(self, model, attrs):
        assert self.lastLoopvar, "found none without for!"
        res = "if not _%s_max_:\n" % self.lastLoopvar
        res = res + indent(self.walk(model), 1)
        return res


    def handle_var(self, model, attrs):
        res = "zres = zres + unicode(scope.get('%s',''))\n" % model[0]
        return res

    def handle_xpr(self, model, attrs):
        res = "zres = zres + unicode(%s)\n" \
              % self.walk(model, mode="exec")
        return res

    def handle_exec(self, model, attrs):
        res = "globals().update(scope)\n" \
              + self.walk(model, mode="exec") + "\n" \
              + "scope.update(globals())\n" \
              + "scope.update(locals())\n"
        return res


    def handle_if(self, model, attrs):
        res = "if %s:\n" % attrs["condition"]
        res = res + indent(self.walk(model), 1)
        return res


    def handle_ef(self, model, attrs):
        res = "elif %s:\n" % attrs["condition"]
        res = res + indent(self.walk(model), 1)
        return res

    def handle_el(self, model, attrs):
        res = "else:\n"
        res = res + indent(self.walk(model), 1)
        return res

    def handle_nl(self, model, attrs):
        return 'zres = zres + "\\n"\n'

    def handle_head(self, model, attrs):
        res = "if %s == 0:\n" % self.loopvars[-1]
        res = res + indent(self.walk(model), 1)
        return res

    def handle_body(self, model, attrs):
        """the body tag does nothing at all.. it's purely aesthetic"""
        return self.walk(model)

    def handle_foot(self, model, attrs):
        res = "if %s + 1 == _%s_max_:\n" % (self.loopvars[-1],
                                            self.loopvars[-1])
        res = res + indent(self.walk(model), 1)
        return res

    def handle_glue(self, model, attrs):
        res = "if %s + 1 < _%s_max_:\n" % (self.loopvars[-1],
                                           self.loopvars[-1])
        res = res + indent(self.walk(model), 1)
        return res

    def handle_include(self, model, attrs):
        res = "import zebra\n"
        res = res + "zres=zres + fetch('%s',scope)\n" % attrs["file"]

        # @TODO: include shouldn't depend on zebra!
        #res = res + "zres = zres+ %s.fetch(scope)\n" % attrs["module"]
        return res
# * utility functions
# ** tests
class ToolsTestCase(unittest.TestCase):

    def test_urlDecode(self):
        """
        check that + signs work right:
        """
        assert handy.urlDecode("+") == " ", \
               "urlDecode screws up on + signs"
        assert handy.urlDecode("%2b") == "+", \
               "urlDecode screws up on %2b"

    def test_html(self):
        #@TODO: make this its own test suite!
        # this shouldn't crash on empty options list:
        select("box", [])



    def setUp(self):
        file = open("junk.zb","w")
        file.write("* for each:\n")
        file.write("    {:a:}\n")
        file.close()

        file = open("xmljunk.zbx", "w")
        file.write(trim(
            '''
            <?xml version="1.0"?>
            <zebra>
            <for series="each">
            <xpr>a</xpr><nl/>
            </for>
            </zebra>
            ''') + "\n")
        file.close()

    def test_fetch(self):
        a = {"a":"x"}
        assert fetch("junk", {"each":[a]}) == "x\n"
        assert fetch("junk.zb", {"each":[a]}) == "x\n"
        assert fetch("xmljunk.zbx", {"each":[a]}) == "x\n"


    def tearDown(self):
        os.unlink("junk.zb")
        os.unlink("xmljunk.zbx")
# ** old_parse
def old_parse(string):
    """
    parse the old, non-xml format
    """
    return Bootstrap().toObject(Z2X().translate(string))
# ** parse
def parse(string):
    """
    parse the xml format
    """
    return Bootstrap().toObject(string)
# ** fetch
def fetch(template, model=None):
    """
    fetch the template, and apply it to the model
    """
    model = model or {}
    path, filename = os.path.split(template)
    cwd = os.getcwd()
    if path:
        os.chdir(path)

    try:
        # @TODO: make the .zb explicit in the call
        if not os.path.exists(filename):
            if os.path.exists(filename + ".zb"):
                filename += ".zb"
            else:
                raise IOError("%s not found" % filename)

        src = open(filename).read()
        if filename.endswith(".zb"):
            rpt = old_parse(src)
        else:
            rpt = parse(src)
        res = rpt.fetch(model)
    finally:
        # cleanup and go home
        os.chdir(cwd)

    return res
# ** show
def show(template, model=None):
    """
    same as fetch(), but prints the result
    """
    print(fetch(template, model))


# ** escape
def escape(s):
    """
    Escape backslashes, quotes, and newlines
    """
    replace = {
        "\\":"\\\\",  # backslash
        "\n":"\\n",   # newline
        "'":"\\'",    # single quote
        "\"":"\\\""   # double quote
        }

    res = ""
    for ch in s:
        if ch in replace.keys():
            res = res + replace[ch]
        else:
            res = res + ch
    return res
# ** trim
def trim(s):
    """trim(s) => Strips leading indentation from a multi-line string."""

    lines = s.split("\n")

    # strip leading blank line
    if lines[0].strip() == "":
        lines = lines[1:]

    # strip indentation
    indent = len(lines[0]) - len(lines[0].lstrip())
    for i in range(len(lines)):
        lines[i] = lines[i][indent:]

    return "\n".join(lines)
# ** indent
def indent(s, depth=1, indenter="    "):
    """indent(s,depth=1,indenter='    ') => Indent a multi-line string."""

    lines = s.split("\n")

    # don't indent trailing newline
    trailer = ""
    if lines[-1] == "":
        lines = lines[:-1]
        # BUT.. add it back in later
        trailer = "\n"

    for i in range(len(lines)):
        lines[i] = (indenter * depth) + lines[i]

    return "\n".join(lines) + trailer


# * html widgets
# ** textarea
def textarea(name, value, attrs=''):
    """
    An html TextArea tag
    """
    return '<textarea name="%s"%s>%s</textarea>' \
           % (name, attrs, xmlEncode(deNone(value)))
# ** checkbox
def checkbox(name, isChecked, onValue=1, offValue=0, attrs=''):
    """
    An html checkbox. Also adds a hidden __expect__ variable
    since the browser doesn\'t often send unchecked checkboxes.
    """
    return '<input type="hidden" name="__expect__" value="%s:%s"/>' \
           '<input type="checkbox" name="%s" %s %s value="%s"/>' \
           % (name, offValue, name, attrs, ['','checked="checked"'][isChecked], onValue)
# ** radio
def radio(name, isChecked, value=1, attrs=''):
    """
    An html radio button.
    """
    return '<input type="radio" name="%s" %s %s value="%s"/>' \
           % (name, attrs, ['','checked="checked"'][isChecked], value)
# ** text
def text(name, value, attrs=''):
    """
    Returns the HTML code for a text INPUT tag.
    """
    return '<input type="text" name="%s" %s value="%s"/>' \
           % (name, attrs, deNone(value))
# ** password
def password(name, value, attrs=''):
    """
    Returns the HTML code for a text PASSWORD tag.
    """
    return '<input type="password" name="%s" %s value="%s"/>' \
           % (name, attrs, deNone(value))
# ** hidden
def hidden(name, value, attrs=''):
    """
    Returns HTML code for a hidden input tag.
    """
    return '<input type="hidden" name="%s" %s value="%s"/>' \
           % (name, attrs, deNone(value))
# ** select
def select(name, options, value=None, attrs=''):
    """
    returns HTML for a select box.
    options is either:
        a sequence of keys (if keys and values are the same)
        a sequence of (key/value) sequences..
    value is either a key or list of keys (can be [])
    attrs is extra HTML to add to the thing..
    """

    ## make sure vals is a list
    if type(value)!=type([]):
        vals = [value]
    else:
        vals = value

    ## expand options into a X*3 grid (if it's not):
    opts = []
    if options:
        # if options is a sequence of sequences:
        if type(options[0]) in (type([]), type(())):
            case = len(options[0])
            ## if options is a list of 3-tuples:
            if case == 3:
                ## leave it as is, ignore values
                opts = options
            ## elif options is a list of 2-tuples:
            elif case == 2:
                ## loop through and add isChecked
                for item in options:
                    opts.append(list(item) + [(item[0] in vals)])
            else:
                raise TypeError("Invalid option structure passed to html.select()!")
        ## else options is a list of keys:
        else:
            ## loop through and add make it [key key isChecked]
            for item in options:
                opts.append([item, item, (item in vals)])
    else:
        pass # kinda silly to want no options, but no point crashing.

    ## now that we have an X*3 grid, show the box:
    res = '<select name="%s" %s>' % (name, attrs)
    for option in  opts:
        res += '<option value="%s"' % option[0]
        if option[2]:
            res += ' selected="selected"'
        res += '>%s</option>' % option[1]
    return res + '</select>'


# * --tests--
if __name__ == "__main__":
    unittest.main()
