
HTTP interface
==============

there's still two interfaces:

  * restful APIs
  * webapps


difference has to do with  how they handle:

   * raise AuthenticationRequired
       * API: HTTP authentication required status code
       * app: /login page
   * redirects to top levels (see "duplicate content", below)
       * 30x / location: ... (same for both, but different base urls?)
   * @onSuccess / @onError
       * not sure restful api should do this at all.
   * POST tunneling
       * not sure restful api should do this either.
   * display of data
       * API: json / xml
       * app: genshi templates [or default (generated) interface?]
   * error handling on POST
       * API: 403 bad request (or whatever) and show raw error in body
       * app: display in @onError page (default to referrer)



Duplicate Content
-----------------

We want to make things easy on spiders, and 
avoid duplicate content.

So:

  GET /user/fred/entries/235/project/entries

should redirect to:

  Location /project/friendlyname/entries



