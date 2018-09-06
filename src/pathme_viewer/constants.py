# -*- coding: utf-8 -*-

"""This module contains all the constants used in PathMe viewer."""

import os

from bio2bel.utils import get_connection
from pathme.cli import WIKIPATHWAYS_DIR


def get_data_dir(module_name):
    """Ensures the appropriate PathMe data directory exists for the given module, then returns the file path

    :param str module_name: The name of the module. Ex: 'pathme'
    :return: The module's data directory
    :rtype: str
    """
    module_name = module_name.lower()
    data_dir = os.path.join(COMPATH_DIR, module_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


MODULE_NAME = 'pathme_viewer'
COMPATH_DIR = os.environ.get('COMPATH_DIRECTORY', os.path.join(os.path.expanduser('~'), '.compath'))
DEFAULT_CACHE_CONNECTION = get_connection(MODULE_NAME)

HUMAN_WIKIPATHWAYS = os.path.join(WIKIPATHWAYS_DIR, 'wp', 'Human')
