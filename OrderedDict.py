"""
OrderedDict
"""

import unittest
import UserDict

# * test
class OrderedDictTest(unittest.TestCase):

    def test_OrderedDict(self):
        ordd = OrderedDict()
        ordd["a"] = 1
        ordd["b"] = 2
        ordd["c"] = 2
        ordd["a"] = 0
        ordd[1] = 1
        assert ordd.keys() == ['a', 'b', 'c'], \
               "keys are wrong: %s" % str(ordd.keys())
        assert ordd[0] == 0, "index is wrong"
        assert ordd[0:2] == [0, 1], \
               "slicing is wrong: %s" % str(ordd[0:2])


    def test_nKeys(self):
        "check numeric keys"
        ordd = OrderedDict()
        ordd[0] = "a"
        ordd[1] = "b"
        assert ordd.keys() == [0, 1], \
               "numeric keys are wrong: %s" % idk.keys()
        


    def test_lshift(self):
        ordd = OrderedDict()
        ordd << "x"
        ordd << "y"
        ordd << "z"
        assert ordd.keys() == [0, 1, 2], \
               "keys are wrong: %s" % str(ordd.keys())
        assert ordd.values() == ["x", "y", "z"], \
               "values are wrong: %s" % str(ordd.values())


    def test_looping(self):
        ordd = OrderedDict()
        for item in ordd:
            assert 0, "there shouldn't be anything in ordd"

        ordd << 1
        for item in ordd:
            assert item==1, "wrong item"

        ordd.clear()
        for item in ordd:
            assert 0, "there shouldn't be anything in ordd after .clear()"


    def test_negative(self):
        ordd = OrderedDict()
        ordd << "abc"
        ordd << "xyz"
        assert ordd[-1] == "xyz", "-1 broke"
        assert ordd[-2] == "abc", "-2 broke"
        try:
            bad = ordd[-3]
            gotError = 0
        except IndexError:
            gotError = 1
        assert gotError, "-3 worked but should not have!"
        

    def test_repr(self):
        """
        really, this just exposes a bug if the keys are numbers...
        """
        ordd = OrderedDict()
        ordd << "zero"
        assert repr(ordd) == "{0: 'zero'}", \
               "wrong representation: %s" % repr(ordd)
# * code

class OrderedDict(UserDict.UserDict):
    __super = UserDict.UserDict

    def __init__(self):
        self.__super.__init__(self)
        self.ordd = []

    def _toStringKey(self, key):
        """Convert numeric keys into string keys. Leaves string keys as is"""
        # handle numeric keys:
        if type(key)==type(0):            
            if not (-len(self.ordd) <= key < len(self.ordd)):
                ## oddly enough, it is this IndexError here
                ## that allows you to do "for x in myOrderedDict:"
                raise IndexError, `key` + " is out of bounds."
            # convert it to a string key
            key = self.ordd[key]
        return key


    def __setitem__(self, key, item):
        """
        we can only use a numeric key if it's bigger than
        the length of the index..
        
        eg,after:
        >>> ordd['a'] = 'abc'
        ordd[0] now maps to "a", so:
        >>> ordd[0] = 'xyz'
        is a reassignment. BUT:
        >>> ordd[1] = 'efg'
        is a normal assignment.

        To handle the magic of figuring out the last index, use 'append':

        >>> ordd.append('hijk')
        >>> ordd.keys()
        ['a', 1, 2]
        >>> ordd[2]
        'hijk'
        """
        
        if (type(key) == type(0)) and (key < len(self.ordd)):
            key = self._toStringKey(key)
                
        if not key in self.ordd:
            self.ordd.append(key)
        self.data[key] = item


    def __getitem__(self, key):
        key = self._toStringKey(key)
        return self.data[key]

    def __repr__(self):
        res = "{"
        for key in self.ordd:
            res = res + repr(key) + ": " + repr(self.data[key]) + ", "

        # strip that last comma and space:
        if len(res) > 1:
            res = res[:-2]

        res = res + "}"
        return res

    #### these are so we can treat it like its a list ######
    def __len__(self):
        return len(self.ordd)

    def clear(self):
        self.__super.clear(self)
        self.ordd = []
    
    def __getslice__(self, i, j):
        i = max(i, 0); j = max(j, 0)
        res = []
        for item in self.ordd[i:j]:
            res.append(self.data[item])
        return res

    def append(self, other):
        self[len(self.ordd)]=other
    
    ### .. or like a dictionary: #########
    def keys(self):
        return self.ordd

    def values(self):
        return self[:]

    ### << is a magical append operator ##########
    def __lshift__(self, other):
        self.append(other)

    #@TODO: what should __delitem__ do??
    # I'm not going to worry about it now, because
    # I don't need to delete anything from my lists.

# * --

if __name__=="__main__":
    unittest.main()
