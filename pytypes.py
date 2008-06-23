"""
python types
"""


# * imports - required
import re
import calendar
import copy
import time
import unittest
from narrative import testcase

# * imports - optional
try:
    import mx.DateTime as mxDateTime
except ImportError:
    mxDateTime = None

try:
    import datetime
except ImportError:
    datetime = None



# * FixedPoint --> replace with 'decimal'
from FixedPoint import FixedPoint
# * DateTime --> replace with datetime.datetime ?
# ** test
class DateTimeTest(unittest.TestCase):

    def test_add(self):
        assert DateTime("1/1/2001 1:23:45") + 1 \
               == DateTime("1/2/2001 1:23:45"), \
               "normal add didn't work."
        assert DateTime("1/31/2001 23:59:59") + 1 \
               == DateTime("2/1/2001 23:59:59"), \
               "end of month didn't work"
        assert DateTime("2/28/2001 0:0:01") + 1 \
               == DateTime("3/1/2001 0:0:01"), \
               "end of month didn't work for february"
        assert DateTime("2/28/2001 1:2:3") + 11 \
               == DateTime("3/11/2001 1:2:3"), \
               "end of month + big number didn't work"
        assert DateTime("12/31/2001 00:00:01") + 1 \
               == DateTime("1/1/2002 0:0:1"), \
               "new year didn't work"
        assert DateTime("1/31/2001 12:00:00") + 31 \
               == DateTime("3/3/2001 12:00:00"), \
               "adding more than a month didn't work"
        assert DateTime("1/1/2001 12:00:00") + 366 \
               == DateTime("1/2/2002 12:00:00"), \
               "adding more than a year didn't work"

    def test_subtract(self):
        assert DateTime("1/2/2001") - 1 \
               == DateTime("1/1/2001"), \
               "normal subtract didn't work."
        assert DateTime("2/1/2001") - 1 \
               == DateTime("1/31/2001"), \
               "end of month didn't work"
        assert DateTime("3/1/2001 1:2:3") - 1 \
               == DateTime("2/28/2001 1:2:3"), \
               "end of month didn't work for february"
        assert DateTime("1/1/2002 0:0:0") - 1 \
               == DateTime("12/31/2001 0:0:0"), \
               "new year didn't work."
        assert DateTime("3/3/2001 23:59:59") - 31 \
               == DateTime("1/31/2001 23:59:59"), \
               "subtracting more than a month didn't work"
        assert DateTime("1/2/2002 1:23:45") - 366 \
               == DateTime("1/1/2001 1:23:45"), \
               "subtracting more than a year didn't work"
        
    def test_convert(self):
        assert Date("1/2/2002") == DateTime("1/2/2002 0:0:0")

    def test_comparisons(self):
        assert DateTime("06/20/1950 08:30:00") \
               == "1950-6-20 8:30:00", "eq string compare"
        assert DateTime("01/01/2001 00:00:00") \
               == Date("01/01/2001"), "eq comparison"
        assert Date("2001-5-1") <= DateTime("5/1/2001 0:0:0"), \
               "le comparison"
        assert Date("5/1/2001") < DateTime("2001-5-1 00:00:01"), \
               "lt comparison"

    def test_todayandnow(self):
        """
        temporarily set time.time() to return 10/19/2001
        and test for today.
        """
        import time
        _time = time.time
        time.time = lambda: 1003539807.89
        try:
            assert DateTime("today") == DateTime("10/19/2001 00:00:00"), \
                   "wrong date from today"
            assert DateTime("now") == DateTime("10/19/2001 21:03:27"), \
                   "wrong date or time from now"
        finally:
            time.time = _time

    def test_gets(self):
        pass

    def test_repr(self):
        d = DateTime('1/1/2001')
        assert repr(d) == "DateTime('01/01/2001 00:00:00')", \
               "wrong __repr__ from datetime"
        d = DateTime('1/1/2001 12:34:56')
        assert repr(d) == "DateTime('01/01/2001 12:34:56')", \
               "wrong __repr__ from datetime"

    def test_daysInMonth(self):
        assert DateTime("1/1/2001").daysInMonth() == 31
        assert DateTime("2/1/2001").daysInMonth() == 28
        assert DateTime("2/1/2000").daysInMonth() == 29
        
    def test_daysInYear(self):
        assert DateTime("1/1/1999").daysInYear() == 365
        assert DateTime("1/1/2000").daysInYear() == 366 # leap year
        assert DateTime("1/1/2001").daysInYear() == 365


    def test_mxDate(self):
        try:
            import mx
            dtNow = DateTime("1/1/2000")
            mxNow = dtNow.toMx()
            assert mxNow == mx.DateTime.DateTime(2000,1,1)
        except ImportError:
            print "[mxDate not installed, skipping test...]"
            

    def test_to_datetime(self):
        try:
            import datetime
            dtNow = DateTime("1/1/2000")
            pyNow = dtNow.to_datetime()
            assert pyNow == datetime.datetime(2000,1,1)
        except ImportError:
            print "[mxDate not installed, skipping test...]"

# ** code
class DateTime:
    """
    A class to represent datetimes.
    """
    def __init__(self, datestr):
        """
        Construct a DateTime from a string representation.
        """
        s = datestr
        if mxDateTime and type(s) == mxDateTime.DateTimeType:
            s = str(s)[:-3] # strip off milliseconds
        elif datetime and (isinstance(s, datetime.datetime)
                           or isinstance(s, datetime.date)):
            s = s.strftime("%Y-%m-%d %H:%M:%S")
        elif type(s) != str:
            raise TypeError, "usage: DateTime(string) (got %s)" % type(s)
        
        if s == "now":
            s = "%04i-%02i-%02i %02i:%02i:%02i" \
                % time.localtime(time.time())[:6]
        elif s == "today":
            s = "%i-%i-%i 00:00:00" % time.localtime(time.time())[:3]
        if " " in s:
            date, timeofday = s.split(" ")
        else:
            date, timeofday = s, None
        # US datetimes:
        if date.find("/") > -1:
            self.m, self.d, self.y = [int(x) for x in date.split("/")]
        # MySQL datetimes:
        else:
            self.y, self.m, self.d = [int(x) for x in date.split("-")]
        if not timeofday:
            self.hh = self.mm = self.ss = 0
        else:
            self.hh, self.mm, self.ss = [int(x) for x in timeofday.split(":")]

    def daysInMonth(self):
        """
        returns number of days in the month
        """
        return calendar.monthrange(self.y, self.m)[1]

    def daysInYear(self):
        from operator import add
        return reduce(add,
                      [calendar.monthrange(self.y, m+1)[1] for m in range(12)])
        
    def toSQL(self):
        return "%i-%i-%i %i:%i:%i" % (self.y, self.m, self.d, self.hh, self.mm, self.ss)

    def toUS(self):
        return "%02i/%02i/%04i %02i:%02i:%02i" % (self.m, self.d, self.y, self.hh, self.mm, self.ss)        

    def __cmp__(self, other):
        if isinstance(other, DateTime):
            return cmp([self.y, self.m, self.d, self.hh, self.mm, self.ss],
                       [other.y, other.m, other.d,
                        other.hh, other.mm, other.ss])
        elif isinstance(other, Date):
            return cmp([self.y, self.m, self.d, self.hh, self.mm, self.ss],
                        [other.y, other.m, other.d, 0, 0, 0])
        else:
            return cmp(self, DateTime(other))

    def __add__(self, days):
        """
        Add a certain number of days, accounting for months, etc..
        """
        res = copy.deepcopy(self)
        res.d += days
        while res.d > res.daysInMonth():
            res.d = res.d - res.daysInMonth()
            res.m += 1
            if res.m > 12:
                res.m = 1
                res.y += 1
        return res
    
    def __sub__(self, days):
        """
        same as __add__, but in reverse..
        """
        res = copy.deepcopy(self)
        res.d -= days
        while res.d < 1:
            res.m -= 1
            if res.m < 1:
                res.m = 12
                res.y -= 1
            res.d += res.daysInMonth()
        return res

    def __str__(self):
        return self.toSQL()

    def __repr__(self):
        return "DateTime('%s')" % self.toUS()

    def toDate(self):
        return Date("%s-%s-%s" % (self.y, self.m, self.d))
    
    def toMx(self):
        "return an mxDateTime if mx is available"
        assert mxDateTime, "mx.DateTime is not installed"
        return mxDateTime.DateTime(self.y, self.m, self.d,
                                   self.hh, self.mm, self.ss)

    def to_datetime(self):
        assert datetime, "datetime is requried here"
        return datetime.datetime(self.y, self.m, self.d,
                                 self.hh, self.mm, self.ss)
# * Date --> replace with datetime.date ?
# ** test
class DateTest(unittest.TestCase):

    def test_add(self):
        assert Date("1/1/2001") + 1 == Date("1/2/2001"), \
               "normal add didn't work."
        assert Date("1/31/2001") + 1 == Date("2/1/2001"), \
               "end of month didn't work"
        assert Date("2/28/2001") + 1 == Date("3/1/2001"), \
               "end of month didn't work for february"
        assert Date("2/28/2001") + 11 == Date("3/11/2001"), \
               "end of month + big number didn't work"
        assert Date("12/31/2001") + 1 == Date("1/1/2002"), \
               "new year didn't work"
        assert Date("1/31/2001") + 31 == Date("3/3/2001"), \
               "adding more than a month didn't work"
        assert Date("1/1/2001") + 366 == Date("1/2/2002"), \
               "adding more than a year didn't work"

    def test_subtract(self):
        assert Date("1/2/2001") - 1 == Date("1/1/2001"), \
               "normal add didn't work."
        assert Date("2/1/2001") - 1 == Date("1/31/2001"), \
               "end of month didn't work"
        assert Date("3/1/2001") - 1 == Date("2/28/2001"), \
               "end of month didn't work for february"
        assert Date("1/1/2002") - 1 == Date("12/31/2001"), \
               "new year didn't work."
        assert Date("3/3/2001") - 31 == Date("1/31/2001"), \
               "subtracting more than a month didn't work"
        assert Date("1/2/2002") - 366 == Date("1/1/2001"), \
               "subtracting more than a year didn't work"
        

    def test_today(self):
        """
        temporarily set time.time() to return 10/19/2001
        and test for today.
        """
        import time
        _time = time.time
        time.time = lambda: 1003539807.89
        try:
            assert Date("today") == Date("10/19/2001"), "wrong date"
        finally:
            time.time = _time

    def test_repr(self):
        d = Date('1/1/2001')
        assert repr(d) == "Date('01/01/2001')", "wrong __repr__"

    def test_daysInMonth(self):
        assert Date("1/1/2001").daysInMonth() == 31
        assert Date("2/1/2001").daysInMonth() == 28
        assert Date("2/1/2000").daysInMonth() == 29
        
    def test_daysInYear(self):
        assert Date("1/1/1999").daysInYear() == 365
        assert Date("1/1/2000").daysInYear() == 366 # leap year
        assert Date("1/1/2001").daysInYear() == 365


@testcase
def test_toDate(self):
    # Date.toDate should return a copy of self
    assert Date("1/1/2000").toDate() == Date("1/1/2000")


# ** code
class Date(DateTime):
    """
    A class to represent dates.
    """
    def __init__(self, datestr):
        """
        Construct a Date from a string representation.
        """
        DateTime.__init__(self, datestr)
        self.hh = self.mm = self.ss = 0

    def toSQL(self):
        res = "%i-%i-%i" % (self.y, self.m, self.d)
        if res =="0-0-0":
            return ''
        else:
            return res

    def toUS(self):
        return "%02i/%02i/%04i" % (self.m, self.d, self.y)        

##     def __cmp__(self, other):
##         if isinstance(other, Date):
##             return cmp([self.y, self.m, self.d], [other.y, other.m, other.d])
##         elif isinstance(other, DateTime):
##             # NOTE: uses arcane DateTime knowledge.
##             # Originally coded as
##             #    return cmp(other, self)*-1
##             return cmp([self.y, self.m, self.d, 0, 0, 0],
##                        [other.y, other.m, other.d,
##                         other.hh, other.mm, other.ss])
##         else:
##             return cmp(self, Date(other))

    def __str__(self):
        return self.toSQL()

    def __repr__(self):
        return "Date('%s')" % self.toUS()
# * Ranges
# ** Range
class Range(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __contains__(self, item):
        raise NotImplementedError(
            "use a Range subclass instead")
# ** ExclusiveRange
class ExclusiveRangeTest(unittest.TestCase):
    def test(self):
        erange = ExclusiveRange(1, 3)
        assert 1 not in erange
        assert 2 in erange
        assert 3 not in erange

class ExclusiveRange(Range):

    def __contains__(self, item):
        return self.left < item < self.right
# ** InclusiveRange

class InclusiveRangeTest(unittest.TestCase):
    def test(self):
        irange = InclusiveRange(1, 3)
        assert 1 in irange
        assert 2 in irange
        assert 3 in irange

class InclusiveRange(Range):

    def __contains__(self, item):
        return self.left <= item <= self.right
    
# ** PythonicRange
class PythonicRangeTest(unittest.TestCase):
    def test(self):
        prange = PythonicRange(1, 3)
        assert 1 in prange
        assert 2 in prange
        assert 3 not in prange

class PythonicRange(Range):
    def __contains__(self, item):
        return self.left <= item < self.right
    
# * toDate --> move to handy?
def toDate(thing):
    """
    ensures that a date is a Date object
    """
    if isinstance(thing, Date):
        return thing
    else:
        return Date(thing)
    
# * toDateTime --> same?
def toDateTime(thing):
    """
    ensures that a datetime is a DateTime object
    """
    if isinstance(thing, DateTime):
        return thing
    else:
        return DateTime(thing)
    
# * dateRange --> ?
def dateRange(date1, date2):
    """
    returns a tuple of Date objects between two dates (inclusive)
    @TODO: this has nothing to do with the Range class
    """
    d1 = toDate(date1)
    d2 = toDate(date2)

    d = d1
    dates = []
    while d <= d2:
        dates.append(d)
        d += 1
    
    return tuple(dates)
# * IdxDict
from OrderedDict import OrderedDict as IdxDict
# * EmailAddress
def email(s):
    try:
        return EmailAddress(s)
    except TypeError:
        return 0

class EmailAddressTest(unittest.TestCase):
  
    def testIt(self):
        assert email('name@example.com')
        assert email('first.last@another-example.com')
        assert email('dash-underscore_first.last+detail.ext@sub.example.com')
        assert not email('laskdjf..asdf@sadf.com')
        assert not email('asdf@@asdf.asc')
        assert not email('aslkdjf')


class EmailAddress(object):

    regex = r'^(\w|\d|_|-|)+(\.[a-zA-Z0-9_\-\+]+)*' \
            r'@(\w|\d|_|-)+(\.[a-zA-Z0-9_\-]+)+$'
    
    def __init__(self, value):
        if not re.match(self.regex, value):
            raise TypeError, "invalid EmailAddress"
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def __cmp__(self, other):
        return cmp(self.value, other)


# * ---
if __name__=="__main__":
    unittest.main()
    
