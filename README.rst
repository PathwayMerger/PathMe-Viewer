PathMe Viewer |build| |coverage| |docs| |zenodo|
================================================

This web application aims to facilitate querying, browsing, and navigating pathway knowledge formalized in Biological Expression Language (BEL). While it was built paralelly with `PathMe <https://github.com/ComPath/PathMe>`_ , to facilitate the exploration of the databases harmonized by this package, the PathMe Viewer supports the visualization of BEL files. 
BEL files can be stored in the PathMe Viewer's database and so they queried in the main page (Figure 1). In this page, users can select multiple BEL files (pathways) to renders the corresponding merged network. The network visualization page (Figure 2) is powered by multiple, built-in functionalities. For instance, when multiple pathways are selected, a novel boundary visualization facilitates the exploration of pathway cross-talks (i.e. the interaction of pathways through their sharing of common entities). Furthermore, search and mining tools enable navigation of the resulting network as well as the identification of contradictory and consensus relationships across pathways. Finally, networks can be exported to multiple formats such as BEL, GraphML, or JSON to be used in other analytical software.

This web application is publicly accessible at http://pathme.scai.fraunhofer.de/ but can be locally deployed using Docker or PyPI (see Installation/Deployment sections).


How to Use
----------
Exploring pathways through this web application is simple. First, select a set of pathways from different databases. To choose a pathway, first select a database and the autocompletion form will then guide you to find pathway(s) of interest to you. After pathways have been selected, click on the "Explore" button to render the merged network corresponding to the selected pathways.

.. image:: https://github.com/ComPath/PathMe-Viewer/blob/master/src/pathme_viewer/static/img/main_page_screenshot.png
    :width: 500px

The resulting network is visualized in the next page where multiple functionalities enable the exploration of the pathway(s).

.. image:: https://github.com/ComPath/PathMe-Viewer/blob/master/src/pathme_viewer/static/img/visualization_example.png
    :width: 500px
    
Installation |pypi_version| |python_versions| |pypi_license|
------------------------------------------------------------

PathMe can be installed easily from `PyPI <https://pypi.python.org/pypi/pathme>`_ running the following code in your terminal:

.. code-block:: sh

    $ python3 -m pip install pathme_viewer

or from the latest code on `GitHub <https://github.com/ComPath/PathMe-Viewer>`_ with:

.. code-block:: sh

    $ python3 -m pip install git+https://github.com/ComPath/PathMe-Viewer.git@master

Database
--------
In order to visualize BEL files with the viwer, you have to load them into the databases. The following command to loads the databases converted to BEL by PathMe (note that the first time it runs might take a couple of hours). Additionally, users can customize the imports to other bel files or databases.

.. code-block:: python

    python3 -m pathme_viewer manage load

In order to check the status of the database, you can run:

.. code-block:: python

    python3 -m pathme_viewer manage summarize

The content of the database can be erased by running:

.. code-block:: python

    python3 -m pathme_viewer manage drop

Deployment
----------
If you have already installed the PathMe-Viewer as a Python package and you have already populated the database, now you can deploy the web application by running:

.. code-block:: python

    python3 -m pip install pathme_viewer web

Note that the database runs by default in the following port: http://0.0.0.0:5000/. The Flask host and port can be
modified by changing the default parameters (run: "python3 -m pathme_viewer web --help" for more info).

Deployment of PathMe Viewer using Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To quickly deploy the web application locally, you can also use Docker. This can be achieved by running the following commands after installing Docker.

1. Build a container named 'pathme' version 0.0.1 (you must be in the root directory after cloning this package with Git).

.. code-block:: sh

    docker build -t pathme:0.0.1 .

2. Run docker the pathme container version 0.0.1.

.. code::

    docker run --name=pathme -d -p 5000:5000 --restart=always -d pathme:0.0.1

Note: the docker file is meant to be run on 0.0.0.0:5000. If you want to change the host/port
please modify dockerfile (line 55) and src/bin/bootstrap.sh (line 23).

 
.. |build| image:: https://travis-ci.org/ComPath/PathMe-Viewer.svg?branch=master
    :target: https://travis-ci.org/ComPath/PathMe-Viewer
    :alt: Build Status

.. |coverage| image:: https://codecov.io/gh/ComPath/PathMe-Viewer/coverage.svg?branch=master
    :target: https://codecov.io/gh/ComPath/PathMe-Viewer?branch=master
    :alt: Coverage Status

.. |docs| image:: http://readthedocs.org/projects/pathme_viewer/badge/?version=latest
    :target: https://pathme_viewer.readthedocs.io/en/latest/
    :alt: Documentation Status

.. |climate| image:: https://codeclimate.com/github/compath/pathme_viewer/badges/gpa.svg
    :target: https://codeclimate.com/github/compath/pathme_viewer
    :alt: Code Climate

.. |python_versions| image:: https://img.shields.io/pypi/pyversions/pathme_viewer.svg
    :alt: Stable Supported Python Versions

.. |pypi_version| image:: https://img.shields.io/pypi/v/pathme_viewer.svg
    :alt: Current version on PyPI

.. |pypi_license| image:: https://img.shields.io/pypi/l/pathme_viewer.svg
    :alt: Apache-2.0

.. |zenodo| image:: https://zenodo.org/badge/144898535.svg
   :target: https://zenodo.org/badge/latestdoi/144898535

