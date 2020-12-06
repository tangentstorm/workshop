
import time
import subprocess
from clockwork import Return, Control

def waitfor(cmd, secondsToWait=0):
    # allow strings or series of strings:
    if type(cmd) is str and " " in cmd:
        cmd = cmd.split()

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1)
    except Exception as e:
        raise Exception("error on %s: %s" % (cmd, e))

    p.killed = False
    start = time.time()
    while p.poll() is None:
        if secondsToWait and (time.time() - start > secondsToWait):
            p.killed = True
            yield waitfor('kill -KILL %s' % p.pid)
            break
        else:
            yield Control
    yield Return(p)
