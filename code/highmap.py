"""
highmap : A high level IMAP library

Python's imaplib gives you back a bunch
of tuples and un-parsed strings that stick
close to the imap4rev1 protocol.

This module wraps imaplib with a limited,
but somewhat cleaner interface.
"""
import unittest
from narrative import testcase
from handy import trim
import imaplib
import email
import email.utils
import textwrap

error = imaplib.IMAP4.error


# * what the imap class looks like:

class MockImap(object):
    """
    This class shows the imaplib.IMAP4 responses from a
    real imap server for a few common requests.

    The methods are arranged according to the order in
    which they would typically be used, so you can read
    this as a partial transcript of an imap session.
    """
    def login(self, username, password):
        "authenticate with the server"
        if password=="correct":
            return (
                'OK',
                ['[CAPABILITY IMAP4REV1 IDLE NAMESPACE MAILBOX-REFERRALS BINARY UNSELECT SCAN SORT THREAD=REFERENCES THREAD=ORDEREDSUBJECT MULTIAPPEND] User %s authenticated' % username])
        else:
            raise error("LOGIN failed")

        
    def list(self, path):
        "list available mailboxes"
        if path == "mail/":
            return ('OK', [
                '(\\NoSelect) "/" mail/',
                '(\\NoInferiors \\UnMarked) "/" mail/INBOX.Drafts',
                '(\\NoInferiors \\UnMarked) "/" mail/Drafts',
                '(\\NoInferiors \\Marked) "/" mail/sent-mail',
                '(\\NoInferiors \\UnMarked) "/" mail/INBOX.Sent',
                '(\\NoInferiors \\UnMarked) "/" mail/INBOX.Trash',
                '(\\NoInferiors \\UnMarked) "/" mail/sent-mail-dec-2006',
                '(\\NoInferiors \\UnMarked) "/" "mail/Sent Items"',
                '(\\NoSelect) "/" mail/afolder',
                '(\\NoInferiors \\UnMarked) "/" mail/afolder/whatever',
                '(\\NoSelect) "/" mail/afolder/subfolder',
                '(\\NoInferiors \\UnMarked) "/" mail/afolder/subfolder/blahblahblah',
                '(\\NoInferiors \\UnMarked) "/" mail/spam'])
        else:
            return ('OK', [None])
                      
    def select(self, box="inbox"):
        "select a mailbox to work with"
        # inbox is a special box required by imap protocol
        if box == "inbox":
            # two messages in box:
            return ('OK', ['2'])        
        else:
            # empty box:
            return ('OK', ['0'])

    def search(self, charset, criteria):
        "search for messages matching the criteria"
        assert criteria=="All"
        return ('OK', ['1 2'])

    def fetch(self, number, what):
        assert number == 1
        assert what == "(RFC822.HEADER UID)"
        return ('OK', [(
            '1 (RFC822.HEADER {1321}',
"""\
Return-Path: <spammy@example.com>
Received: from imf13bis.bellsouth.net (mail313.mail.bellsouth.net [205.152.58.173])
        by example.com (8.11.6/8.11.6) with ESMTP id g9DLb1J10964
        for <ftempy@example.com>; Sun, 13 Oct 2002 17:37:01 -0400
Received: from [192.168.1.102] ([67.34.142.150]) by imf13bis.bellsouth.net
        (InterMail vM.5.01.04.19 201-253-122-122-119-20020516) with ESMTP
        id <20021013213825.WPHV371.imf13bis.bellsouth.net@[192.168.1.102]>
        for <ftempy@example.com>; Sun, 13 Oct 2002 17:38:25 -0400
Date: Sun, 13 Oct 2002 17:29:43 -0400 (Eastern Daylight Time)
From: Spammy Spammer <spammy@example.com>
Subject: *****SPAM***** SPAM SPAM SPAM 234234
To: ftempy@example.com
Message-ID: <Mahogany-0.64.2-4294614661-20021013-172943.00@c-24-98-91-150.atl.client2.attbi.com>
MIME-Version: 1.0
Content-Type: TEXT/PLAIN; CHARSET=US-ASCII
Content-Disposition: INLINE
Organization: Spammy Spammers, Inc
X-Mailer: SpamMailer 1.2
X-Spam-Status: Yes, hits=5.5 required=5.0
       tests=DOUBLE_CAPSWORD,CLICK_BELOW,UPPERCASE_75_100,SUBJ_ALL_CAPS
       version=2.31
X-Spam-Flag: YES
X-Spam-Level: *****
X-Spam-Checker-Version: SpamAssassin 2.31 (devel $Id: highmap.py,v 1.3 2008/05/29 00:51:47 sabren Exp $)


"""), ' UID 1 FLAGS (\\Seen))'])

# * now for the tests:

def mock(): return HIMAP(MockImap())

@testcase
def instantiate(test):
    hi = mock()
    test.assertRaises(error, hi.login, "ftempy", "incorrect")
    hi.login("ftempy", "correct")

@testcase
def test_list_empty(test):
    hi = mock()
    
    


# * implementation

class HIMAP(object):

    def __init__(self, imap):
        self.imap = imap

    def login(self, user, pw):
        return self.imap.login(user, pw)



# * unprocessed code

#@TODO: make this data driven!
def tags(msg):
    sub = (msg["subject"] or '').lower()
    if sub.count("urgent"):
        yield "urgent"
    if sub.count("contact"):
        yield "contact"
    if sub.count("order]"):
        yield "order"
    if sub.count("error in control panel"):
        yield "error"
    if (sub.startswith("Item #")
    or  sub.startswith("payment")):    
        yield "money"
    if sub.count("[innercircle]"):
        yield "list"


def simpleFrom(f):
    if f.startswith('"'):
        return f.split('"')[1]
    elif f.startswith("<"):
        return f
    elif f.count("<"):
        return f.split("<")[0]
    else:
        return f


def getMessage(imap, boxname, uid):
    stat, data = imap.search(None, "(UID %s)" % uid)
    if stat == "OK" and bool(data[0]):
        msgid = data[0]
        _, data = imap.fetch(msgid, "(RFC822)")
        message = data[0][1]
        msg = email.message_from_string(message)
        return msg
    else:
        return None # raise error?


def headers(msg, uid):
    return {"from" : simpleFrom(msg["from"]),
            "subject": msg["subject"],
            "uid" : uid,
            "message-id": msg["message-Id"],
            'date': msg['date'],
            'datetup' : email.utils.parsedate(msg['date']),
            "tags": " ".join(tags(msg))}


def message(imap, num, headersOnly=False):
    """
    returns the email.Message object  and uid
    """
    format = "(RFC822.HEADER UID)" if headersOnly else "(RFC822 UID)"
    _, data = imap.fetch(num, format)
    msg = email.message_from_string(data[0][1])
    uid = "".join([c for c in data[1] if c.isdigit()])
    return uid, msg


def messages(imap, boxname, headersOnly=False):
    """
    yields uid, message object for each message in box
    """
    imap.select(boxname)
    _, nums = imap.search(None, "ALL")
    for num in nums[0].split():
        yield message(imap, num, headersOnly)


def index(imap, boxname):
    for uid, msg in messages(imap, boxname):
        yield headers(msg, uid)




def paragraphs(text):
    # loosly based on brett cannon's recipe:
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/358228
    accum = []
    blank = ""
    plain, quoted = object(), object()
    state = plain

    if type(text) is list:
        for msg in text:
            if msg.get_content_type() == "text/plain":
                yield msg.get_payload()
                raise StopIteration
        else:
            yield str(msg)[0]
            raise StopIteration

    for line in text.split("\n"):
        if line.strip() == blank:
            if accum:
                yield textwrap.fill(" ".join(accum))
                accum = []
            yield "\n"
        elif line.startswith(">"):
            if accum:
                yield textwrap.fill(" ".join(accum)); accum=[]
            pass
        elif line.startswith("\t") or line.startswith(" "):
            yield line
        else:
            accum.append(line)


# * run tests
if __name__=="__main__":
    unittest.main()
