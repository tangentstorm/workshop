
Configure a Storage System
==========================

Types of Storage
----------------

  * MySQL
  * SQLite
  * other relational databases
  * non-relational storage (imap, text files, etc)


Define a Database Connection
----------------------------
@TODO: set up makeClerk based on $APPNAME.app


Create the Clerk
----------------
add to $APPNAME.py:

from clerks import Clerk
from storage import dbc

def makeClerk():
    clerks.Clerk(SCHEMA(dbmap), MySQLStorage(dbc))


