
import cursor
import unittest
from narrative import testcase

"""
Generic cursors. The cursor should be tied to a view, because
you want to move up and down based on the visible rows,
skipping over rows that might be hidden.

This means the view should be able to take a particular
index and return the index of the next visible row, going
either up or down.
"""

@testcase
def testListView(self):
    view = cursor.ListView(list("012"))
    self.assertEquals(0, view.indexPrevious(0))
    self.assertEquals(0, view.indexPrevious(1))
    self.assertEquals(2, view.indexNext(1))
    self.assertEquals(2, view.indexNext(2))
    

@testcase
def testZoomView(self):

    out = ["zero","one","two","three","four","five"]

    view = cursor.ZoomView(out)
    view.selectWhere(lambda row: row.startswith('t'))
    assert not view.selected[0]
    assert view.selected[2]
    assert not view.selected[4]

    view.zoom()
    assert list(view.visible()) == ["two", "three"]

    view.unzoom()
    assert list(view.visible()) == ["zero","one","two","three","four","five"]




@testcase
def testMoveNext(self):
    """
    Now that we know the zoomview is working, let's make
    sure we can navigate the zoomed list correctly. This
    is really a test that the cursor correctly calls
    indexNext and indexPrevious
    """

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    view = cursor.ZoomView(alphabet)

    c = cursor.Cursor(view)
    assert c.value() == "a"

    view.selectWhere(lambda row: row in "aeiou")

    view.zoom()
    c.moveDown()
    assert c.value() == "e"

    view.unzoom()
    assert c.value() == "e"

    c.moveUp()
    assert c.value() == "d"

    # note that if we zoom again while the cursor is
    # on something that will be hidden, the cursor itself
    # is hidden. It's your responsibility to move the cusor
    # up or down after the zoom.
    view.zoom()
    assert c.value() == "d"


@testcase
def testCursor(self):

    class SomeView:
        def indexFirst(self): return 50        
        def indexLast(self): return 75
        def indexPrevious(self, x): return x -2
        def indexNext(self, x): return x+5
        
    c = cursor.Cursor(SomeView())
    self.assertEquals(50, c.position)

    c.moveToBottom()
    self.assertEquals(75, c.position)
    
    c.moveUp()
    self.assertEquals(73, c.position)

    c.moveToTop()
    self.assertEquals(50, c.position)

    c.moveDown()
    self.assertEquals(55, c.position)



if __name__=="__main__":
    unittest.main()
