
Using Themes
============

Use any Template Engine
-----------------------
You should be able to use this scheme with *any* template engine.
So long as it takes:

   - model (dictionary)
   - filename (minus the extension)

Themes can be placed under /themes/
Themes should have a theme.ini.

Example:

  themes/mygenshi/theme.ini

There *must* be a default theme set. By default, it's called default. :)


mapping urls to apps
---------------------

The  urlmap looks a lot like the restful API urlmap:

  GET /whatver = app.whatever
  GET /whatver?x=y = app.whatever.match(x='y')
  GET /whatever/1 = app.whatever[1]
  POST /whatever = app.whatever << formdata     # append (with adaptation)
  PUT /whatever/1 = app.whatever[1] = formdata  # assign (with adaptation)
  DELETE = /whatever/1 = del app.whatever[1]

But... We also need to use a theme.

For the most part, templates can be auto-discovered based on the url:


for all app.xxx:

  GET /xxx = search for:
      - themes/default/xxx.gen
      - themes/default/xxx-list.gen

  GET /xxx/yyy = search for:
      - themes/default/xxx-item.gen

  # nothing should expose this: themes/default/layout.gen

  GET /login = themes/default/login.gen
  POST /login @onSuccess = the page you wanted before :)

  on error: form[@onError] or show themes/default/error.gen 

  GET /whatever         themes/default/whatever-list.gen
  GET /whatever?new     themes/default/whatever-edit.gen unless -create.gen is there
  GET /whatever/1       themes/default/whatever-show.gen
  GET /whatever/1?edit  themes/default/whatever-edit.gen

  YAGNI: themes/default/message.gen ?? # if distinct from error??


adding custom templates and uris
--------------------------------

Something like this:

  URI("/crontab", 
      GET = theme('crontab'), 
      PUT = remote.SetCrontab)

hrm.. but really, why not use the same logic for app.crontab ? 

# inheritance:
  def get_crontab(self, value): pass
  def set_crontab(self, value): pass
  crontab = property(get_crontab, set_crontab)


# composition:
  app.crontab = property(remote.getCrontab, remote.setCrontab)
  

naming conventions
------------------

  url        py
  ------------------
  xx/yy  ->  xx['yy']
  xx?yy  ->  xx('yy')
  xx-yy  ->  xx_yy
  xx.yy  ->  xx.yy    # but generally not used (??)

