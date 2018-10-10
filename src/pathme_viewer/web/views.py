# -*- coding: utf-8 -*-

"""This module contains the PathMe views."""

import datetime
import logging
import sys

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request
)
from flask_admin.contrib.sqla import ModelView
from pkg_resources import resource_filename

from ..graph_utils import export_graph, merge_pathways, get_tree_annotations, process_request
from ..models import Pathway

log = logging.getLogger(__name__)
time_instantiated = str(datetime.datetime.now())

pathme = Blueprint(
    'pathme_viewer',
    __name__,
    template_folder=resource_filename('pathme_viewer', 'templates'),
    static_folder=resource_filename('pathme_viewer', 'templates')
)

redirect = Blueprint(
    '',
    __name__,
    template_folder=resource_filename('pathme_viewer', 'templates'),
    static_folder=resource_filename('pathme_viewer', 'templates')
)


class PathwayView(ModelView):
    """Pathway view in Flask-admin."""

    column_searchable_list = (
        Pathway.name,
        Pathway.resource_name,
        Pathway.pathway_id,
        Pathway.created,
        Pathway.number_of_nodes,
        Pathway.number_of_edges,
        Pathway.version,
        Pathway.pybel_version,
        Pathway.contact,
        Pathway.authors,
        Pathway.description,
    )
    column_list = (
        Pathway.name,
        Pathway.resource_name,
        Pathway.pathway_id,
        Pathway.created,
        Pathway.number_of_nodes,
        Pathway.number_of_edges,
        Pathway.version,
        Pathway.pybel_version,
        Pathway.contact,
        Pathway.authors,
        Pathway.description,
    )


"""Redirection to home page"""


@redirect.route('/')
def home():
    """Redirect to PathMe page. Only used when PathMe is run independent from ComPath."""
    return render_template('pathme.html')


"""Views"""


@pathme.route('/pathme')
def home():
    """PathMe home page."""
    return render_template('pathme.html')


@pathme.route('/pathme/about')
def about():
    """Render About page. Only when is run independent from ComPath"""
    metadata = [
        ('Python Version', sys.version),
        ('Deployed', time_instantiated),
        ('KEGG Version', current_app.pathme_manager.get_pathway_by_id('', 'kegg')),
        ('Reactome Version', current_app.pathme_manager.get_pathway_by_id('', 'reactome')),
        ('WikiPathways Version', current_app.pathme_manager.get_pathway_by_id('WP100', 'wikipathways').created),
    ]
    # TODO: add info about population of networks

    return render_template('meta/pathme_about.html', metadata=metadata)


@pathme.route('/pathme/viewer')
def viewer():
    """PathMe page."""
    pathways = process_request(request)

    return render_template(
        'pathme_viewer.html',
        pathways=pathways,
        pathway_ids=list(pathways.keys())
    )


@pathme.route('/api/pathway/')
def get_network():
    """Builds a graph from request and sends it in the given format."""
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    log.info('Exporting graph with {} nodes and {} edges'.format(graph.number_of_nodes(), graph.number_of_edges()))

    return export_graph(graph, request.args.get('format'))


@pathme.route('/api/tree/')
def get_network_tree():
    """Builds a graph and sends the annotation ready to be rendered in the tree."""
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    # Returns annotation in graph
    return jsonify(get_tree_annotations(graph))


@pathme.route('/admin/delete/pathways')
def delete_pathways():
    """Delete all pathways."""
    current_app.pathme_manager.delete_all_pathways()

    return jsonify(
        status=200,
        message='All Pathways have been deleted',
    )


@pathme.route('/api/autocompletion/pathway_name')
def api_pathway_autocompletion_resource_specific():
    """Autocompletion for pathway name given a database.
        ---
        tags:
          - autocompletion
        responses:
          200:
            description: returns a list for the autocompletion of 10 pathway in JSON.
     """
    q = request.args.get('q')
    resource = request.args.get('resource')

    if not q or not resource:
        return jsonify([])

    query_results = current_app.pathme_manager.query_pathway_by_name_and_resource(q, resource, limit=10)

    if not query_results:
        return jsonify([])

    return jsonify([
        {'label': pathway.name, 'value': pathway.pathway_id}
        for pathway in query_results
    ])
