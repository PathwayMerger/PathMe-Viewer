# -*- coding: utf-8 -*-

"""Command line interface."""

from __future__ import print_function

import logging
import os

import click
from pathme.constants import DATA_DIR, KEGG, RDF_WIKIPATHWAYS, REACTOME, WIKIPATHWAYS
from pathme.utils import make_downloader
from pathme.wikipathways.utils import (
    get_file_name_from_url,
    unzip_file
)

from .constants import DEFAULT_CACHE_CONNECTION
from .load_db import load_wikipathways, load_reactome
from .manager import Manager
from .models import Base

log = logging.getLogger(__name__)

KEGG_DIR = os.path.join(DATA_DIR, KEGG)
REACTOME_DIR = os.path.join(DATA_DIR, REACTOME)
WIKIPATHWAYS_DIR = os.path.join(DATA_DIR, WIKIPATHWAYS)

# Ensure data folders are created
os.makedirs(KEGG_DIR, exist_ok=True)
os.makedirs(REACTOME_DIR, exist_ok=True)
os.makedirs(WIKIPATHWAYS_DIR, exist_ok=True)


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
def web(host, port):
    """Run web service."""

    from .web.web import create_app
    app = create_app()
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
def load_database(connection, kegg_path, reactome_path, wikipathways_path):
    """Loads pathways into Database"""

    """Load KEGG"""

    """Load WikiPathways"""
    cached_file = os.path.join(WIKIPATHWAYS_DIR, get_file_name_from_url(RDF_WIKIPATHWAYS))
    make_downloader(RDF_WIKIPATHWAYS, cached_file, WIKIPATHWAYS, unzip_file)

    manager = Manager.from_connection(connection=connection)

    load_wikipathways(manager, wikipathways_path)

    """Load Reactome"""

    load_reactome(manager, reactome_path)


@manage.command(help='Summarizes Entries in Database')
@click.option('-c', '--connection', help='Defaults to {}'.format(DEFAULT_CACHE_CONNECTION))
def summarize(connection):
    """Summarize all."""
    m = Manager.from_connection(connection=connection)

    click.echo('The database contains {} pathways'.format(m.count_pathways()))


if __name__ == '__main__':
    main()
