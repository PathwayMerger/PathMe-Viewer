# -*- coding: utf-8 -*-

"""This module contains all the constants used in PathMe viewer."""

import os

from pathme.constants import get_connection, KEGG, REACTOME, WIKIPATHWAYS, WIKIPATHWAYS_FILES

DATABASE_STYLE_DICT = {
    KEGG: 'KEGG',
    REACTOME: 'Reactome',
    WIKIPATHWAYS: 'WikiPathways',
}

DATABASE_URL_DICT = {
    KEGG: 'http://www.kegg.jp/kegg-bin/show_pathway?map=map{}&show_description=show',
    REACTOME: 'https://reactome.org/PathwayBrowser/#/{}',
    WIKIPATHWAYS: 'https://www.wikipathways.org/index.php/Pathway:{}'
}

MODULE_NAME = 'pathme_viewer'
PATHME_DIR = os.environ.get('PATHME_DIRECTORY', os.path.join(os.path.expanduser('~'), '.pathme'))
DEFAULT_CACHE_CONNECTION = get_connection(MODULE_NAME)

HUMAN_WIKIPATHWAYS = os.path.join(WIKIPATHWAYS_FILES, 'wp', 'Human')

FORMAT = 'format'
PATHWAYS_ARGUMENT = 'pathways[]'
RESOURCES_ARGUMENT = 'resources[]'
UNDIRECTED = 'undirected'
PATHS_METHOD = 'paths_method'
RANDOM_PATH = 'random'
COLLAPSE_TO_GENES = 'collapse_to_genes'

BLACK_LIST = {
    COLLAPSE_TO_GENES,
    FORMAT,
    PATHWAYS_ARGUMENT,
    RESOURCES_ARGUMENT,
    UNDIRECTED,
    PATHS_METHOD,
    RANDOM_PATH,
}
