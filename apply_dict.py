"""
apply a dictionary to a callable
"""
import inspect
import unittest
import narrative as narr

@narr.testcase
def test_the_rationale(test):
    """
    the ** calling syntax works great when the arguments
    match the parameter definition exactly, but it has
    problems when you have extra fields but no **kw parameter.
    """

    def function(a, b, c, d=123):
        return (a, b, c, d)

    goal  = (1, 2, 3, 123)
    exact = {"a":1, "b":2, "c":3}
    extra = {"a":1, "b":2, "c":3, "e":4}

    test.assertEquals(goal, function(**exact))

    try:
        function(**extra)
    except TypeError:
        pass
    else:
        test.fail("?!! That should have raised TypeError.")


@narr.testcase
def test_apply_dict(test):
    """
    apply_dict is like the calling ** syntax but ignores extra keywords
    """

    def function(a, b, c, d=123):
        return (a, b, c, d)

    goal  = (1, 2, 3, 123)
    extra = {"a":1, "b":2, "c":3, "e":4}
    test.assertEquals(goal, apply_dict(function, extra))


@narr.testcase
def test_apply_dict_evil(test):
    """
    however, extra keywords are still passed to a ** parameter
    """
    def get_keywords(a, b, **kw):
        return kw

    args = {"a":1, "b":2, "c":3, "d": 4}
    goal = {              "c":3, "d": 4}
    test.assertEquals(goal, apply_dict(get_keywords, args))


def default_arg_dict(args, defaults):
    res = {}
    if defaults:
        # n defaults map to last n arguments
        argsWithDefaults = args[-len(defaults):]
        for key, val in zip(argsWithDefaults, defaults):
            res[key] = val
    return res


def dict_subset(dict, keys):
    """
    returns a smaller (subset) dict containing only the named arguments
    """
    res = {}
    for key in keys:
        if dict.has_key(key):
            res[key] = dict[key]
    return res


def apply_dict(fun, dict):

    args, vargs, kwargs, defaults = inspect.getargspec(fun)

    # we don't support vargs def f(*vargs): because dicts are unordered
    if vargs:
        raise NotImplementedError("apply_dict doesn't support vargs")

    # we don't handle nested args yet f(a, (b, c), d)
    for item in args:
        if type(item) == tuple:
            raise NotImplementedError("apply_dict doesn't support nested args")


    if kwargs:
        collected = dict
    else:
        collected = default_arg_dict(args, defaults)
        collected.update(dict_subset(dict, args))
    
    # now apply those arguments
    return fun(**collected)

if __name__=="__main__":
    unittest.main()
    
