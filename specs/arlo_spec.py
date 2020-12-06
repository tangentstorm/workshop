from arlo import _, declare, StartExpr, Name, pattern
import unittest


class ArloTest(unittest.TestCase):

    def want(self, clause, goal, format=str):
        self.assertEquals(format(clause), goal)

    @staticmethod
    def test_type():
        """
        The most basic property of our system is that
        all expressions are reified. So here, _(0)<_(1)
        should evaluate to an Expr, NOT a boolean.
        
        Overriding __lt__ (and the other magic methods
        specified at http://docs.python.org/library/operator.html)
        should do the trick. The docs specifically say:

        > Note that unlike the built-in cmp(), these functions
        > can return any value, which may or may not be interpretable
        > as a Boolean value.

        This was working fine in the original arlo, built with
        python 2.5, but was broken by 2.7. So this first one
        is also a regression test.
        """
        assert type(_(0) < _(1)) != bool

    def test_Const(self):
        self.want(_(5), "5")

    def test_simple(self):
        self.want(_.a < _(5),  "(a < 5)")

    def test_string_vs_field(self):
        self.want(_.f == _('f'),  "(f == 'f')")

    def test_complex(self): 
        self.want((_.a == 1) | (_.b == 2),
                  "((a == 1) | (b == 2))")

    def test_like(self):
        self.want(_.name.like("a"),
                  "name.like('a')")

    def test_declare_0(self):
        exec(declare('x'))
        self.want(_.defun.f(x)[x+1],
                  "defun.f(x)[(x + 1)]")

    def test_getitem(self):
        self.want(_.x[42],  "x[42]")
        self.want(_.x[4, 2], "x[4,2]")
        self.want(_.f(_.x)[4, 2], "f(x)[4,2]")

    def test_getattr(self):
        self.want(_.x, "x")
        self.want(_.x + 1, "(x + 1)")
        self.want(_.x.meth, "x.meth")
        self.want(_.x.meth(42), "x.meth(42)")

    def test_repr(self):
        def rep(c, g): self.want(c, g, format=repr)
        rep(_.x, "_.x")
        rep(_.x + 1, "(_.x + _(1))")
        rep(_.x.meth, "_.x.meth")
        rep(_.x.meth(2), "_.x.meth(_(2))")

    def test_declare(self):
        assert declare("a b c") == "a,b,c = _.a,_.b,_.c"

    def test_in(self):
        """
        Would have been nice to have an 'in' operator,
        but apparently __contains__ is always coerced into
        a boolean, no matter what it returns. :/
        """
        class Group(object):
            def __contains__(self, x):
                return "asdfghjk"

        assert (52 in Group()) is True, str(52 in Group())

    def test_pattern(self):
        assert pattern(_) == ()
        self.assertEquals((StartExpr(), Name('x')), pattern(_.x))
        
    def test_mega_parse(self):

        exec(declare("data sig let IO Num Ord Str undefined where"))
        exec(declare("a b c   p q y   x z y   xs zs"))
        exec(declare("CLASS YIELD RETURN SET DEF SELF INIT"))

        CODE = (
            data. Peano [ _.Zero
                        | _.Succ.Peano ],

            data. Tree.a [ _.Leaf.a
                         | _.Branch.a .Tree .Tree ],

            let. myTree == _.Branch(_.Plus) .Leaf(2) .Leaf(2),

            sig. myAdd == Num >> Num ,
            let. myAdd (_, 0) == 0,
            let. myAdd (x, 0) == x,

            sig. fact == Num >> Num,
            let. fact(0) == 1,
            let. fact(x) == x * _.fact(x -1),

            sig. qsort == Ord.a >> [a] >> [a],
            let. qsort([]) == [] ,
            let. qsort(_[p:xs]) == (_.qsort.lesser + [p] + _.qsort.greater,
                where (
                   # @TODO: keyword arguments
                   _.lesser == [y | y << xs, y < p],
                   _.greater == [y | y << xs, y >= p] )),

            sig. showTree >> Str, 
            let. showTree[_.Tree, _.Tree] == undefined,

            sig. main >> IO._,
            let. main == undefined,

            # a python-like dsl:
            CLASS. Imperative(_(object))[
                DEF. INIT(SELF, _.name)[
                    SET. SELF.name == _.name 
                ],
                DEF. hello(SELF, _.name)[
                    YIELD.  _("hello %s") % SELF.name ]])

        # for item in CODE: print "\n%s\n" % item

if __name__ == '__main__':
    unittest.main()
