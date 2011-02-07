"""
This lets you create win32 application bars with wxPython.

(Application bars are windows that dock to the desktop and stay visible when
you maximize other windows, like the windows task bar.)

Usage:

   # to make a window into an appbar:
   from wxappbars import SetAppBar, ABEdge
   SetAppBar(win, ABEdge.Left)

   # to restore the window:
   SetAppBar(win, ABEdge.Float)


This is a port of the c# code from:

  http://stackoverflow.com/questions/75785/how-do-you-do-appbar-docking-to-screen-edge-like-winamp-in-wpf

With help from:

   http://wxappbar.sourceforge.net

(Which did the same thing, but doesn't seem to work anymore, as of python 2.7
and wxPython 2.8.11)
"""
from ctypes import wintypes
from ctypes import *
import wx

shell32 = windll.shell32
user32 = windll.user32
import win32api, win32con, win32gui

class APPBARDATA(Structure):
    _fields_= [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.c_ulong),
        ("uEdge", c_ulong),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]
PAPPBARDATA = POINTER(APPBARDATA)


class ABEdge:
    Left = 0
    Top = 1
    Right = 2
    Bottom = 3
    Float = 4


class ABMsg:
    ABM_NEW = 0
    ABM_REMOVE = 1
    ABM_QUERYPOS = 2
    ABM_SETPOS = 3
    ABM_GETSTATE = 4
    ABM_GETTASKBARPOS = 5
    ABM_ACTIVATE = 6
    ABM_GETAUTOHIDEBAR = 7
    ABM_SETAUTOHIDEBAR = 8
    ABM_WINDOWPOSCHANGED = 9
    ABM_SETSTATE = 10


class ABNotify:
    ABN_STATECHANGE = 0
    ABN_POSCHANGED = 1
    ABN_FULLSCREENAPP = 2
    ABN_WINDOWARRANGE = 3




class RegisterInfo(object):

    def __init__(self):
        self._window = None

        self.callbackId = 0
        self.isRegistered = False
        self.edge = ABEdge.Float
        self.originalStyle = None
        self.originalPosition = None
        self.originalSize = None
        self.originalResizeMode = None


    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, window):
        self._window = window
        self._hWnd = window.GetHandle()
        self._oldWndProc = win32gui.SetWindowLong(self._hWnd,
                                                 win32con.GWL_WNDPROC,
                                                 self.WndProc)

    # http://wiki.wxpython.org/HookingTheWndProc
    def WndProc(self, hWnd, msg, wParam, lParam ):
        if msg == win32con.WM_DESTROY:
            self._restoreOldWndProc()
        elif msg == self.callbackId:
            if wParam == ABNotify.ABN_POSCHANGED:
                _ABSetPos(self.edge, self.window)
        else:
            return win32gui.\
                CallWindowProc(self._oldWndProc, hWnd, msg, wParam, lParam)


    def _restoreOldWndProc(self):
        win32api.SetWindowLong(self._hWnd,
                               win32con.GWL_WNDPROC,
                               self._oldWndProc)




_registeredWindowInfo = {}
def _GetRegisterInfo(appbarWindow):
    if not _registeredWindowInfo.has_key(appbarWindow):
        reg = RegisterInfo()
        reg.callBackId = 0
        reg.window = appbarWindow
        reg.isRegistered = False
        reg.edge = ABEdge.Top
        reg.originalStyle = appbarWindow.GetWindowStyle()
        reg.originalPosition = appbarWindow.GetPosition()
        reg.originalSize = appbarWindow.GetSize()
        _registeredWindowInfo[appbarWindow] = reg
    return _registeredWindowInfo[appbarWindow]


def _RestoreWindow(appbarWindow):
    info = _GetRegisterInfo(appbarWindow)
    appbarWindow.SetWindowStyle(info.originalStyle)
    appbarWindow.SetPosition(info.originalPosition)
    appbarWindow.SetSize(info.originalSize)
    appbarWindow.SetResizeMode(info.originalResizeMode)

def SetAppBar(appbarWindow, edge):

    info = _GetRegisterInfo(appbarWindow)
    info.edge = edge
    abd = APPBARDATA()
    abd.cbSize = wintypes.DWORD(sizeof(abd))
    abd.hWnd = wintypes.HWND(appbarWindow.GetHandle())

    if (edge == ABEdge.Float) and info.isRegistered:
        shell32.SHAppBarMessage(ABMsg.ABM_REMOVE, PAPPBARDATA(abd))
        info.isRegistered = False
        _RestoreWindow(appbarWindow)

    elif not info.isRegistered:
        info.isRegistered = True
        info.callbackId = win32api.RegisterWindowMessage("AppBarMessage")
        shell32.SHAppBarMessage(ABMsg.ABM_NEW, PAPPBARDATA(abd))

    appbarWindow.SetWindowStyle(wx.BORDER_NONE | wx.STAY_ON_TOP)
    _ABSetPos(info.edge, appbarWindow)


def _DoResize(appBarWindow, rect):
    appBarWindow.SetSize((rect.Width, rect.Height))
    appBarWindow.SetPosition((rect.Left, rect.Top))


def _ABSetPos(edge, appbarWindow):
    barData = APPBARDATA()
    barData.cbSize = wintypes.DWORD(sizeof(barData))
    barData.hWnd = appbarWindow.GetHandle()
    barData.uEdge = edge

    deskW = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_X)
    deskH = wx.SystemSettings_GetMetric(wx.SYS_SCREEN_Y)
    winW, winH = appbarWindow.Size

    if barData.uEdge == ABEdge.Left or barData.uEdge == ABEdge.Right:
        barData.rc.top = 0
        barData.rc.bottom = deskH
        if barData.uEdge == ABEdge.Left:
            barData.rc.left = 0
            barData.rc.right = winW
        else:
            barData.rc.right = deskW
            barData.rc.left = deskW - winW
    else:
        barData.rc.left = 0
        barData.rc.right = deskW
        if barData.uEdge == ABEdge.Top:
            barData.rc.top = 0
            barData.rc.bottom = winH
        else:
            barData.rc.bottom = deskH
            barData.rc.top = deskH - winH


    shell32.SHAppBarMessage(ABMsg.ABM_QUERYPOS, PAPPBARDATA(barData))
    shell32.SHAppBarMessage(ABMsg.ABM_SETPOS, PAPPBARDATA(barData))


    def _resize():
        appbarWindow.SetPosition((barData.rc.left, barData.rc.top))
        appbarWindow.SetSize((barData.rc.right - barData.rc.left,
                              barData.rc.bottom - barData.rc.top))

    # This is done async, because windows will send a resize after a new appbar is added.
    # if we size right away, the windows resize comes last and overrides us.
    wx.CallAfter(_resize)


if __name__=="__main__":
    # This just creates a window with a giant 'close' button
    # and docks it on the left side of the screen.
    app = wx.App(redirect=False)
    win = wx.Frame(None, -1, "i am the appbar")
    btn = wx.Button(win, -1, "[click to close]")
    btn.Bind(wx.EVT_BUTTON, lambda e :  win.Destroy())
    SetAppBar(win, ABEdge.Left)
    win.Show()
    app.MainLoop()

