
Platonic CRUD
=============

    >>> import timesheet0
    >>> app = timesheet0.Timesheet0App()

A Resource Oriented Architecture
--------------------------------

Create
......

    >>> len(app.people)
    0

    >>> from model import Person
    >>> app.people <<< Person(fname='fred', lname='tempy')
    >>> len(app.people)
    1


Retrieve
........

You can retrieve by ID:

    >>> app.people[1].fname
    'fred'

    >>> app.people << dict(fname='rufus', lname='tempy')
    >>> app.people[2].fname
    'rufus'


Update
......

    >>> def update(rufus):
    ...     rufus.email = "rufus@tempytantrum.com"
    >>> app.people[2].with_do(update)
    >>> app.people[2].email
    'rufus@tempytantrum.com'


Delete
......
	
    >>> len(app.people)
    2
    >>> del app.people[2]
    >>> len(app.people)
    1

Advanced Usage
..............

You can use a dictionary instead of an object:

    >>> app.people << dict(fname='wanda', lname='tempy')
    >>> len(app.people)
    2

    >>> [(person.ID, person.fname) for person in app.people]
    [(1L, 'fred'), (3L, 'wanda')]


@TODO: Allow unique string as alias for keys.
GET /user/username = app.user[username]


app.user[user1] = matchOne(**{stringKeyField:"user1"})
app.user[user1,user2,user3] = match(where(lambda u=User: u.username in ("user1","user2","user3")))
