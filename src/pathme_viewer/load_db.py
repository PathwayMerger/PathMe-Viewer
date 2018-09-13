# -*- coding: utf-8 -*-

"""Utils to load the PathMe database."""

import logging
import os

import tqdm

from pathme.cli import KEGG_DIR, REACTOME_DIR
from pathme.constants import KEGG, REACTOME, RDF_REACTOME, WIKIPATHWAYS
from pathme.kegg.convert_to_bel import kegg_to_bel
from pathme.reactome.rdf_sparql import reactome_to_bel
from pathme.reactome.utils import untar_file
from pathme.utils import make_downloader, get_files_in_folder
from pathme.wikipathways.rdf_sparql import wikipathways_to_bel
from pathme.wikipathways.utils import (
    get_file_name_from_url,
    get_wikipathways_files
)
from pybel import to_bytes
from .constants import HUMAN_WIKIPATHWAYS

log = logging.getLogger(__name__)


def import_folder(manager, folder, files, conversion_method, database, **kwargs):
    """General function to import a folder into database.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param str folder: folder to be imported
    :param iter[str] files: iterator with file names
    :param str database: resource name
    """
    for file_name in tqdm.tqdm(files, desc='Loading {} graphs into PathMe database'.format(database)):
        file_path = os.path.join(folder, file_name)

        bel_pathway = conversion_method(file_path, **kwargs)

        pathway_info = {
            'pathway_id': os.path.splitext(file_name)[0],
            'resource_name': database,
            'name': bel_pathway.document['name'],
            'version': bel_pathway.document['version'],
            'authors': bel_pathway.document['authors'],
            'contact': bel_pathway.document['contact'],
            'description': bel_pathway.document.get('description'),
            'pybel_version': bel_pathway.pybel_version,
            'blob': to_bytes(bel_pathway)
        }

        _ = manager.get_or_create_pathway(pathway_info)

    log.info('%s has been loaded', database)


def load_kegg(manager, hgnc_manager, chebi_manager, folder=None):
    """Load KEGG files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param bio2bel_hgnc.Manager hgnc_manager: HGNC manager
    :param bio2bel_chebi.Manager chebi_manager: ChEBI manager
    :param str folder: folder
    """
    kegg_data_folder = folder or KEGG_DIR

    kgml_files = get_files_in_folder(kegg_data_folder)

    if not kgml_files:
        log.warning("There are no KGML files in %s. Please run 'python3 -m pathme kegg download'", kegg_data_folder)

    import_folder(
        manager,
        kegg_data_folder,
        kgml_files,
        kegg_to_bel,
        KEGG,
        hgnc_manager=hgnc_manager,
        chebi_manager=chebi_manager
    )


def load_reactome(manager, hgnc_manager, folder=None):
    """Load Reactome files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param Optional[str] folder: folder
    """
    reactome_data_folder = folder or REACTOME_DIR

    cached_file = os.path.join(reactome_data_folder, get_file_name_from_url(RDF_REACTOME))
    make_downloader(RDF_REACTOME, cached_file, REACTOME, untar_file)

    import_folder(
        manager,
        reactome_data_folder,
        ['Homo_sapiens.owl'],
        reactome_to_bel,
        REACTOME,
        hgnc_manager=hgnc_manager
    )


def load_wikipathways(manager, folder=None, connection=None, only_canonical=True):
    """Load WikiPathways files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param Optional[str] folder: folder
    :param Optional[str] connection: database connection
    :param Optional[bool] only_canonical: only identifiers present in WP bio2bel db
    """
    wikipathways_data_folder = folder or HUMAN_WIKIPATHWAYS

    files = get_wikipathways_files(
        wikipathways_data_folder,
        connection,
        only_canonical
    )

    import_folder(manager, wikipathways_data_folder, files, wikipathways_to_bel, WIKIPATHWAYS)
