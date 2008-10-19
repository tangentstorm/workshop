"""
handy routines for python
"""
from pytypes import Date
import htmlentitydefs
import md5
import operator
import os
import random
import string
import sys
import tempfile
import urllib

try: from Ft.Xml.Domlette import NonvalidatingReader
except: pass

try: from genshi.template.text import NewTextTemplate
except: pass

ZETTA = 10**21
EXA   = 10**18
PETA  = 10**15
TERA  = 10**12
GIGA  = 10**9
MEGA  = 10**6
KILO  = 10**3


def debug(password='abc123'):
    import rpdb2
    rpdb2.start_embedded_debugger(
        password, fAllowUnencrypted=True, fAllowRemote=True)
    

class switch(object):
    """
    syntactic sugar for multiple dispatch

    this idea is taken from:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/410692
    
    it's modified slightly because I didn't want
    the 'fall through' behavior that required break
    """
    def __init__(self, value):
        self.value = value

    def __iter__(self):
        """
        this lets you do 'for case in switch()'
        """
        yield self.match
        raise StopIteration
    
    def match(self, *args):
        return self.value in args



def daysInMonthPriorTo(day):
    return (day - day.d).d


def daysInLastMonth():
    return daysInMonthPriorTo(Date("today"))



def randpass(length=5):    
    okay = "abcdefghijkmnopqrstuvwxyz2345678923456789"
    res = ""
    for i in range(length+1):
        res += okay[random.randrange(0, len(okay))]
    return res


def reconcile(seriesA, seriesB):
    extraA = [x for x in seriesA if x not in seriesB]
    extraB = [x for x in seriesB if x not in seriesA]
    return (extraA, extraB)


def readable(bytes):
    """
    convert a bytecount into human-readable text
    """
    x = bytes
    b = x % 1000; x-=b; x/=1000
    k = x % 1000; x-=k; x/=1000
    m = x % 1000; x-=m; x/=1000
    g = x % 1000; x-=g; x/=1000
    if g: return str(g) + "." + string.zfill(str(m),3)[0] + "G"
    if m: return str(m) + "." + string.zfill(str(k),3)[0] + "M"
    if k: return str(k) + "." + string.zfill(str(b),3)[0] + "k"
    return str(b)


def sendmail(mail):
    sender = os.popen("/usr/sbin/sendmail -t", "w")
    sender.write(mail)
    sender.close()


def trim(s):
    """
    strips leading indentation from a multi-line string.
    for saving bandwith while making code look nice
    """
    lines = string.split(s, "\n")

    # strip leading blank line
    if lines[0] == "":
        lines = lines[1:]
        
    # strip indentation
    indent = len(lines[0]) - len(string.lstrip(lines[0]))
    for i in range(len(lines)):
        lines[i] = lines[i][indent:]

    return string.join(lines, "\n")


def indent(s, depth=1, indenter="    "):
    """
    opposite of trim
    """
    lines = string.split(s, "\n")

    # don't indent trailing newline
    trailer = ""
    if lines[-1] == "":
        lines = lines[:-1]
        # BUT.. add it back in later
        trailer = "\n"
        
    for i in range(len(lines)):
        lines[i] = (indenter * depth) + lines[i]
        
    return string.join(lines, "\n") + trailer
   

def uid():
    """
    unique identifier generator, for sessions, etc
    Returns a 32 character, printable, unique string
    """
    tmp, uid = "", ""
    
    # first, just get some random numbers
    for i in range(64):
        tmp = tmp + chr(random.randint(0,255))

    # then make a 16-byte md5 digest...
    tmp = md5.new(tmp).digest()

    # and, since md5 is unprintable,
    # reformat it in hexidecimal:
    for i in tmp:
        uid = uid + string.zfill(hex(ord(i))[2:],2)        

    return uid


def edit(s):
    """
    launch an editor...
    """
    ed = os.environ.get("EDITOR", "vi")
    fn = tempfile.mktemp()
    tf = open(fn,"w")
    tf.write(s)
    tf.close()
    os.system("%s %s" % (ed, fn))
    return open(fn).read()



def sum(series, initial=None):
    return reduce(operator.add, series, 0)
assert sum((1,2,3)) == 6


class Everything:
    def __contains__(self, thing):
        return True
Everything=Everything()
assert 234324 in Everything



def deNone(s, replacement=''):
    """
    replaces None with the replacement string
    """
    # if s won't be zero, you might as well use:
    # "s or ''" instead of "deNone(s)"
    if s is None:
        return replacement
    else:
        return s


def genshiText(indented_string):
    t = NewTextTemplate(trim(indented_string))
    return lambda **kw: t.generate(**kw).render()


def urlDecode(what):
    res = None

    if type(what) == type(""):
        res = urllib.unquote(string.replace(what, "+", " "))

    elif type(what) == type({}):
        res = urllib.urldecode(what)
    else:
        raise "urlDecode doesn't know how to deal with this kind of data"

    return res



def htmlEncode(s):
    _entitymap = dict((val, key) for (key,val) in htmlentitydefs.entitydefs.items())
    res = ""
    if s is not None:
        for ch in s:
            if _entitymap.has_key(ch):
                res = res + "&" + _entitymap[ch] + ";"
            else:
                res = res + ch
    return res
        


def take(howMany, series):
    count = 0
    for thing in series:
        yield thing
        count += 1
        print count
        if count >= howMany: break


def xml(s):
    """
    parse the xml and return a Ft.Xml.Domlette
    """
    return NonvalidatingReader.parseString(s)


def xmlEncode(s):
    """
    xmlEncode(s) ->  s with >, <, and & escaped as &gt;, &lt; and &amp;
    """
    res = ""
    for ch in s:
        if ch == ">":
            res = res + "&gt;"
        elif ch=="<":
            res = res + "&lt;"
        elif ch=="&":
            res=res + "&amp;"
        else:
            res = res + ch
    return res


class Proxy(object):
    def __init__(self, obj):
        self.__dict__['obj'] = obj

    def __getattr__(self, slot):
        return getattr(self.obj, slot)

    def __getitem__(self, slot):
        return self.obj[slot]

    def __setattr__(self, slot, value):
        setattr(self.obj, slot, value)

    def __setitem__(self, slot, value):
        self.obj[slot] = value
