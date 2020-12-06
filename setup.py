from common_setup import *
setup(
    name = "workshop",
    description = "webAppWorkshop tools and dependencies",
    install_requires = [

        # some of these are separate:
        'strongbox',

        # Sphinx
        'docutils>=0.3', 'Sphinx', 'Pygments', 

        # Paste
        'Paste', 'PasteScript', 'PasteDeploy', 'CherryPy',

        # genshi
        'genshi', 
    ],
    **common
)
