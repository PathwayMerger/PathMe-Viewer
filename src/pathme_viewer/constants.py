# -*- coding: utf-8 -*-

"""This module contains all the constants used in PathMe viewer."""

import os

from pathme.cli import WIKIPATHWAYS_FILES
from pathme.constants import get_connection, KEGG, REACTOME, WIKIPATHWAYS

DATABASE_STYLE_DICT = {
    KEGG: 'KEGG',
    REACTOME: 'Reactome',
    WIKIPATHWAYS: 'WikiPathways',
}

MODULE_NAME = 'pathme_viewer'
PATHME_DIR = os.environ.get('PATHME_DIRECTORY', os.path.join(os.path.expanduser('~'), '.pathme'))
DEFAULT_CACHE_CONNECTION = get_connection(MODULE_NAME)

HUMAN_WIKIPATHWAYS = os.path.join(WIKIPATHWAYS_FILES, 'wp', 'Human')

PATHWAYS_ARGUMENT = 'pathways[]'
RESOURCES_ARGUMENT = 'resources[]'
UNDIRECTED = 'undirected'
PATHS_METHOD = 'paths_method'
RANDOM_PATH = 'random'
