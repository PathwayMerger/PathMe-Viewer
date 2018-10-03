# -*- coding: utf-8 -*-

"""Command line interface."""

from __future__ import print_function

import logging
import os

import click
from bio2bel_chebi import Manager as ChebiManager
from bio2bel_hgnc import Manager as HgncManager
from pybel import union

from pathme.constants import (
    KEGG,
    KEGG_DIR,
    RDF_WIKIPATHWAYS,
    REACTOME,
    REACTOME_DIR,
    WIKIPATHWAYS,
    WIKIPATHWAYS_DIR,
    ensure_pathme_folders
)
from pathme.utils import make_downloader
from pathme.wikipathways.utils import (
    get_file_name_from_url,
    unzip_file
)
from .constants import DEFAULT_CACHE_CONNECTION
from .load_db import load_kegg, load_reactome, load_wikipathways
from .manager import Manager
from .models import Base

log = logging.getLogger(__name__)

# Ensure data folders are created
ensure_pathme_folders()


def set_debug(level):
    """Set debug."""
    log.setLevel(level=level)


def set_debug_param(debug):
    """Set parameter."""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)


@click.group(help='PathMe')
def main():
    """Main click method"""
    logging.basicConfig(level=20, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")


@main.command()
@click.option('--host', default='0.0.0.0', help='Flask host. Defaults to 0.0.0.0')
@click.option('--port', type=int, default=5000, help='Flask port. Defaults to 5000')
@click.option('--template', help='Defaults to "../templates"')
@click.option('--static', help='Defaults to "../static"')
def web(host, port, template, static):
    """Run web service."""
    from .web.web import create_app
    app = create_app(template_folder=template, static_folder=static)
    app.run(host=host, port=port)


@main.group()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.pass_context
def manage(ctx, connection):
    """Manage the database."""
    ctx.obj = Manager.from_connection(connection)
    Base.metadata.bind = ctx.obj.engine
    Base.query = ctx.obj.session.query_property()
    ctx.obj.create_all()


@manage.command(help='Delete all database entries')
@click.option('-v', '--debug', count=True, help="Turn on debugging.")
@click.option('-y', '--yes', is_flag=True)
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
def drop(debug, yes, connection):
    """Drop PathMe DB."""
    set_debug_param(debug)

    if yes or click.confirm('Do you really want to delete the PathMe DB'):
        m = Manager.from_connection(connection=connection)
        click.echo('Deleting PathMe DB')
        m.drop_all()
        m.create_all()


@manage.command(help='Load Pathways')
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.option('-kp', '--kegg_path', help='KEGG data folder. Defaults to {}'.format(KEGG_DIR))
@click.option('-rp', '--reactome_path', help='Reactome data folder. Defaults to {}'.format(REACTOME_DIR))
@click.option('-wp', '--wikipathways_path', help='WikiPathways data folder. Defaults to {}'.format(WIKIPATHWAYS_DIR))
@click.option('-f', '--flatten', help='Flat complexes/composites. Defaults to False')
def load_database(connection, kegg_path, reactome_path, wikipathways_path, flatten):
    """Loads databases into PathMe DB."""
    manager = Manager.from_connection(connection=connection)

    log.info('Initiating HGNC Manager')
    hgnc_manager = HgncManager()

    log.info('Initiating ChEBI Manager')
    chebi_manager = ChebiManager()

    """Load KEGG"""

    # User must agree to KEGG License
    if click.confirm(
            'You are about to download KGML files from KEGG.\n'
            'Please make sure you have read KEGG license (see: https://www.kegg.jp/kegg/rest/).'
            ' These files cannot be distributed and their use must be exclusively academic.\n'
            'We (PathMe developers) are not responsible for the end use of this data.\n'
    ):
        click.echo('You have read and accepted the conditions stated above.\n')

        # Check if kegg is already in the database
        kegg_pathways = manager.get_pathways_by_resource(KEGG)

        if len(kegg_pathways) < 300:
            load_kegg(manager, hgnc_manager, chebi_manager, kegg_path, flatten)
        else:
            log.info('KEGG seems to be already in the database')

    """Load WikiPathways"""

    cached_file = os.path.join(WIKIPATHWAYS_DIR, get_file_name_from_url(RDF_WIKIPATHWAYS))
    make_downloader(RDF_WIKIPATHWAYS, cached_file, WIKIPATHWAYS, unzip_file)

    # Check if wikipathways is already in the database
    wikipathways_pathways = manager.get_pathways_by_resource(WIKIPATHWAYS)

    if len(wikipathways_pathways) < 300:
        load_wikipathways(manager, wikipathways_path)
    else:
        log.info('WikiPathways seems to be already in the database')

    """Load Reactome"""

    # Check if Reactome is already in the database
    reactome_pathways = manager.get_pathways_by_resource(REACTOME)

    if len(reactome_pathways) < 2000:
        load_reactome(manager, hgnc_manager, reactome_path)
    else:
        log.info('Reactome seems to be already in the database')


@manage.command(help='Summarizes Entries in Database')
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
def summarize(connection):
    """Summarize all."""
    m = Manager.from_connection(connection=connection)

    click.echo('The database contains {} pathways'.format(m.count_pathways()))


@manage.command(help='Export pathways to tsv')
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
@click.option('-a', '--all', is_flag=True)
def export_to_tsv(connection, all):
    """Summarize all."""
    m = Manager.from_connection(connection=connection)

    if all:
        pathways = [
            pathway.as_bel()
            for pathway in m.get_all_pathways()
        ]

        graph = union(pathways)

        with open("pathme_triplets.tsv", "w") as f:
            for sub, obj, data in graph.edges(data=True):
                print("%s\t%s\t%s" % (sub.as_bel(), data['relation'], obj.as_bel()), file=f)


if __name__ == '__main__':
    main()
