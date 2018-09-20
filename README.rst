PathMe Viewer
=============

This plugin initializes the pathway viewer in ComPath that allows to explore overlaps between pathways using
the canonical mappings.


Installation
------------
1. ``pathme_viewer`` can be installed with the following commands:

.. code-block:: sh

    $ python3 -m pip install git+https://github.com/ComPath/PathMe-Viewer.git@master

2. or in editable mode with:

.. code-block:: sh

    $ git clone https://github.com/ComPath/PathMe-Viewer.git
    $ cd PathMe-Viewer
    $ python3 -m pip install -e .


Database
--------
The web application requires to load the pathways from the databases in the BEL. Thus, it is required to the following
command to load the database (note that the first time it runs might take a couple of hours).

.. code-block:: python

    python3 -m pathme_viewer manage load_database

In order to check the status of the database, you can run:

.. code-block:: python

    python3 -m pathme_viewer manage summarize

The content of the database can be erased by running:

.. code-block:: python

    python3 -m pathme_viewer manage drop

Deployment
----------
Once the desired pathway databases are loaded, you can deploy the web application by running:

.. code-block:: python

    python3 -m pip install pathme_viewer web

Note that the database runs by default in the following port: http://0.0.0.0:5000/. The Flask host and port can be
modified by changing the default parameters (run: "python3 -m pathme_viewer web --help" for more info).