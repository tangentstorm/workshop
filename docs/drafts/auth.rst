
Authentication
--------------
Platonic has a generic protocol for Authentication.

- one class per app should be the "user" class.
- optionally, users can be assigned to roles


def authenticated(user):
    if user is Anonymous:
        raise AuthenticationRequired
    return user


Convention could be to do this:

    def handler(_user):
        pass

    class MyApp(...):
        def specials(self):
            return lazydict(
               _user = lambda : authenticated(self.user))

     
