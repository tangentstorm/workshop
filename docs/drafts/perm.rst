Permissions
===========

    @rule(RETRIEVE, SomePublicResource)
    def _(self, user, spr):
        return True

    @rule(RETRIEVE, SomeProtectedResource)
    def _(self, user, spr):
        return authenticated(user)


generic permission issues
-------------------------

We need to be able to control how deeply
someone can navigate into the tree... 

here are some benign cases:

  fred = app.people['ftempy']
  fred.entries             # you'd want that.
  fred.entries[235]        # what if 235 does not belong to ftempy?
  fred.entries[235].person # okay, but ugly.

But what about this:

  fred.entries[235].project.entries  

That could give access entries by other users. Maybe that's okay.
But, the permission framework needs to handle that.

It should only show the entries your user is allowed to see.


If we allow a distinction between the generic app and
the user's view of the app, then these are different:

   sess.people['ftempy'].entries[235].project.entries  
   app.people['ftempy'].entries[235].project.entries

Whereas, if the app requires a user in the constructor
(even if it's an anonymous user) then there's no
distinction between the app and the user's view of the app.

I think this latter situation is the right move.



