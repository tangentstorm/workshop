
from tracker import *
from fields import *
from storage import MockStorage
import shelve

stor= PySQLiteStorage(getDB("tracker.db", itemSchema)) 
app = TrackerApp(stor)
app.DEFAULT="tables"
app.dispatch(REQ, RES)
