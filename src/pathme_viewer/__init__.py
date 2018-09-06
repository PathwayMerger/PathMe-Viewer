# -*- coding: utf-8 -*-

"""PathMe Viewer. A plugin for PathMe that allows to explore overlaps across pathway databases.
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

__version__ = '0.0.1'

__title__ = 'pathme_viewer'
__description__ = "A plugin for PathMe that allows to explore overlaps across pathway databases."
__url__ = 'https://github.com/ComPath/PathMe-Viewer'

__author__ = 'Daniel Domingo-Fernandez'
__email__ = 'daniel.domingo.fernandez@scai.fraunhofer.de'

__license__ = 'MIT License'
__copyright__ = 'Copyright (c) 2017-2018 Daniel Domingo-Fernandez'
