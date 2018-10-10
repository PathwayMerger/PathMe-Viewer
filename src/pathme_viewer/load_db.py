# -*- coding: utf-8 -*-

"""Utils to load the PathMe database."""

import logging
import os

import tqdm

from pathme.cli import KEGG_FILES, REACTOME_FILES
from pathme.constants import KEGG, KEGG_BEL, REACTOME, REACTOME_BEL, RDF_REACTOME, WIKIPATHWAYS, WIKIPATHWAYS_BEL
from pathme.kegg.convert_to_bel import kegg_to_bel
from pathme.kegg.utils import download_kgml_files, get_kegg_pathway_ids
from pathme.reactome.rdf_sparql import reactome_to_bel
from pathme.reactome.utils import untar_file
from pathme.utils import make_downloader, get_files_in_folder
from pathme.wikipathways.rdf_sparql import wikipathways_to_bel
from pathme.wikipathways.utils import get_file_name_from_url, get_wikipathways_files
from pybel import from_pickle, to_bytes
from .constants import HUMAN_WIKIPATHWAYS

log = logging.getLogger(__name__)


def _prepare_pathway_model(pathway_id, database, bel_graph):
    """Prepare dictionary pathway model.

    :param str pathway_id: identifier
    :param str database: database name
    :param pybel.BELGraph bel_graph: graph
    :rtype: dict
    :return: pathway model in dict
    """
    return {
        'pathway_id': pathway_id,
        'resource_name': database,
        'name': bel_graph.document['name'],
        'version': bel_graph.document['version'],
        'number_of_nodes': bel_graph.number_of_nodes(),
        'number_of_edges': bel_graph.number_of_edges(),
        'authors': bel_graph.document['authors'],
        'contact': bel_graph.document['contact'],
        'description': bel_graph.document.get('description')
        if isinstance(bel_graph.document.get('description'), str)
        else '{}'.format(bel_graph.document.get('description')),
        'pybel_version': bel_graph.pybel_version,
        'blob': to_bytes(bel_graph)
    }


def import_from_pickle(manager, folder, files, database):
    """Import folder with pickles into database.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param str folder: folder to be imported
    :param iter[str] files: iterator with file names
    :param str database: resource name
    """
    for file_name in tqdm.tqdm(files, desc='Loading {} pickles to populate PathMe database'.format(database)):
        file_path = os.path.join(folder, file_name)

        bel_pathway = from_pickle(file_path)

        pathway_id = os.path.splitext(file_name)[0]

        # KEGG files have a special format (prefix: unflatten/flatten needs to be removed)
        if database == KEGG:
            pathway_id = pathway_id.split('_')[0]

        pathway_dict = _prepare_pathway_model(pathway_id, database, bel_pathway)

        _ = manager.get_or_create_pathway(pathway_dict)

    log.info('%s has been loaded', database)


def import_from_pathme(manager, folder, files, conversion_method, database, **kwargs):
    """Import a given folder into database based on a conversion method.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param str folder: folder to be imported
    :param iter[str] files: iterator with file names
    :param str database: resource name
    """
    for file_name in tqdm.tqdm(files, desc='Converting {} to BEL to populate PathMe database'.format(database)):
        file_path = os.path.join(folder, file_name)

        bel_pathway = conversion_method(file_path, **kwargs)

        pathway_dict = _prepare_pathway_model(os.path.splitext(file_name)[0], database, bel_pathway)

        _ = manager.get_or_create_pathway(pathway_dict)

    log.info('%s has been loaded', database)


def load_kegg(manager, hgnc_manager, chebi_manager, folder=None, flatten=None):
    """Load KEGG files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param bio2bel_hgnc.Manager hgnc_manager: HGNC manager
    :param bio2bel_chebi.Manager chebi_manager: ChEBI manager
    :param str folder: folder
    :param Optional[bool] flatten: flatten or not
    """
    # 1. Check if there are pickles in the KEGG folder. If there are already pickles, use them to populate db
    pickles = get_files_in_folder(KEGG_BEL)

    if pickles:
        log.info('You seem to already have created BEL Graphs using PathMe. The database will be populated using those')
        import_from_pickle(manager, KEGG_BEL, pickles, KEGG)

    else:
        # 2. Check that KGML files are already downloaded
        kegg_data_folder = folder or KEGG_FILES

        kgml_files = get_files_in_folder(kegg_data_folder)

        # Skip not KGML files
        kgml_files = [
            file
            for file in kgml_files
            if file.endswith('.xml')
        ]

        # If there are no KGML files, download them or ask the user to populate Bio2BEL KEGG
        if not kgml_files:
            log.warning("There are no KGML files in %s. Using Bio2BEL KEGG to download them.'", kegg_data_folder)
            kegg_ids = get_kegg_pathway_ids()

            download_kgml_files(kegg_ids)

        # 3. Parse KGML files to populate DB
        import_from_pathme(
            manager,
            kegg_data_folder,
            kgml_files,
            kegg_to_bel,
            KEGG,
            hgnc_manager=hgnc_manager,
            chebi_manager=chebi_manager,
            flatten=True if flatten is True else False
        )


def load_reactome(manager, hgnc_manager, folder=None):
    """Load Reactome files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param bio2bel_hgnc.manager.Manager hgnc_manager: HGNC manager
    :param Optional[str] folder: folder
    """
    # 1. Check if there are pickles in the Reactome folder. If there are already pickles, use them to populate db
    pickles = get_files_in_folder(REACTOME_BEL)

    if pickles:
        log.info('You seem to already have created BEL Graphs using PathMe. The database will be populated using those')
        import_from_pickle(manager, REACTOME_BEL, pickles, REACTOME)

    else:
        # 2. Check if RDF files are downloaded, if not download them
        reactome_data_folder = folder or REACTOME_FILES

        cached_file = os.path.join(reactome_data_folder, get_file_name_from_url(RDF_REACTOME))
        make_downloader(RDF_REACTOME, cached_file, reactome_data_folder, untar_file)

        # 3. Parse RDF file to populate DB
        import_from_pathme(
            manager,
            reactome_data_folder,
            ['Homo_sapiens.owl'],
            reactome_to_bel,
            REACTOME,
            hgnc_manager=hgnc_manager
        )


def load_wikipathways(manager, hgnc_manager, folder=None, connection=None, only_canonical=True):
    """Load WikiPathways files in PathMe DB.

    :param pathme_viewer.manager.Manager manager: PathMe manager
    :param bio2bel_hgnc.manager.Manager hgnc_manager: HGNC manager
    :param Optional[str] folder: folder
    :param Optional[str] connection: database connection
    :param Optional[bool] only_canonical: only identifiers present in WP bio2bel db
    """
    # 1. Check if there are pickles in the WikiPathways folder. If there are already pickles, use them to populate db
    pickles = get_files_in_folder(WIKIPATHWAYS_BEL)

    if pickles:
        log.info('You seem to already have created BEL Graphs using PathMe. The database will be populated using those')
        import_from_pickle(manager, WIKIPATHWAYS_BEL, pickles, WIKIPATHWAYS)

    else:
        # 2. Check if RDF files are downloaded, if not download them
        wikipathways_data_folder = folder or HUMAN_WIKIPATHWAYS

        files = get_wikipathways_files(
            wikipathways_data_folder,
            connection,
            only_canonical
        )

        # 3. Parse RDF file to populate DB
        import_from_pathme(
            manager,
            wikipathways_data_folder,
            files,
            wikipathways_to_bel,
            WIKIPATHWAYS,
            hgnc_manager=hgnc_manager
        )
