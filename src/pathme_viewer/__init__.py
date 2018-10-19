# -*- coding: utf-8 -*-

"""PathMe Viewer.

A plugin for PathMe that allows to explore pathway knowledge.

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

"""

import logging

from compath.constants import MODULE_NAME
from compath_utils import CompathManager
from pkg_resources import VersionConflict, iter_entry_points, UnknownExtra

log = logging.getLogger(__name__)

managers = {}

for entry_point in iter_entry_points(group=MODULE_NAME, name=None):
    entry = entry_point.name

    try:
        bio2bel_module = entry_point.load()
    except UnknownExtra:
        log.warning('Unknown extra in %s', entry)
        continue
    except VersionConflict:
        log.warning('Version conflict in %s', entry)
        continue

    try:
        ExternalManager = bio2bel_module.Manager
    except AttributeError:
        log.warning('%s does not have a top-level Manager class', entry)
        continue

    if not issubclass(ExternalManager, CompathManager):
        log.warning('%s:%s is not a standard ComPath manager class', entry, ExternalManager)

    managers[entry] = ExternalManager

__version__ = '0.0.2'

__title__ = 'pathme_viewer'
__description__ = "A plugin for PathMe that allows to explore overlaps across pathway databases."
__url__ = 'https://github.com/ComPath/PathMe-Viewer'

__author__ = 'Daniel Domingo-Fernandez'
__email__ = 'daniel.domingo.fernandez@scai.fraunhofer.de'

__license__ = 'MIT License'
__copyright__ = 'Copyright (c) 2017-2018 Daniel Domingo-Fernandez'
