from wherewolf import *
import unittest

class SQLTest(unittest.TestCase):
    def test_where(self):
        self.assertEquals( sql(where.x > 10) , "(x > 10)")
        self.assertEquals( sql( ((where.x+1) < 50) | (where.name == "Fred")),
                           "(((x + 1) < 50) OR (name = 'Fred'))")

        self.assertEquals( sql(where.name % 'f%') , "(name LIKE 'f%')")
        self.assertEquals( sql(where.a & where.b) , "(a AND b)")

    def test_escape(self):
        self.assertEquals( sql(where.x == "I'm") , "(x = 'I''m')")

    def test_pyLike(self):
        self.assertEquals(toPython(where.name % 'f%'), "name.startswith('f')")
        self.assertEquals(toPython(where.name % '%d'), "name.endswith('d')")
        self.assertEquals(toPython(where.name % 'f.*d'), "re.match('f.*d', name)")
        self.assertEquals(toPython(where.name % 5), "(name % 5)")

if __name__=="__main__":
    unittest.main()
