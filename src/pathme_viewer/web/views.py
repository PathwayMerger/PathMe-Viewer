# -*- coding: utf-8 -*-

"""This module contains the PathMe views."""

import datetime
import logging
import sys
from operator import itemgetter

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request
)
from flask_admin.contrib.sqla import ModelView
from networkx import NetworkXNoPath, all_simple_paths, betweenness_centrality, shortest_path
from pkg_resources import resource_filename
from pybel import from_bytes
from pybel.struct import get_random_path
from pybel.struct.mutation.collapse import collapse_to_genes
from pybel_tools.selection import get_subgraph_by_annotations

from pathme_viewer.constants import (
    COLLAPSE_TO_GENES,
    DATABASE_STYLE_DICT,
    DATABASE_URL_DICT,
    PATHS_METHOD,
    RANDOM_PATH,
    UNDIRECTED
)
from pathme_viewer.graph_utils import (
    export_graph,
    get_annotations_from_request,
    get_tree_annotations,
    merge_pathways,
    prepare_venn_diagram_data,
    process_request,
    process_overlap_for_venn_diagram
)
from pathme_viewer.models import Pathway

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
    return render_template('home.html')


"""Views"""


@pathme.route('/pathme')
def home():
    """PathMe home page."""
    return render_template('home.html')

@pathme.route('/imprint')
def imprint():
    """Render the Imprint page."""
    return render_template('meta/imprint.html')

@pathme.route('/pathme/about')
def about():
    """Render About page. Only when is run independent from ComPath"""
    example_kegg = current_app.pathme_manager.get_pathway_by_id('hsa00010', 'kegg')
    example_reactome = current_app.pathme_manager.get_pathway_by_id('R-HSA-109581', 'reactome')
    example_wp = current_app.pathme_manager.get_pathway_by_id('WP100', 'wikipathways')
    metadata = [
        ('Python Version', sys.version),
        ('Deployed', time_instantiated),
        ('KEGG Version', example_kegg.created if example_kegg else ''),
        ('Reactome Version', example_reactome.created if example_reactome else ''),
        ('WikiPathways Version', example_wp.created if example_wp else ''),
    ]

    return render_template('meta/about.html', metadata=metadata)


@pathme.route('/tutorial')
def tutorial():
    """Render the tutorial page"""
    return render_template('meta/help.html')


@pathme.route('/admin/delete/pathways')
def delete_pathways():
    """Delete all pathways."""
    current_app.pathme_manager.delete_all_pathways()

    return jsonify(
        status=200,
        message='All Pathways have been deleted',
    )


@pathme.route('/pathway/node')
def get_pathways_with_node():
    """Return all pathways having a given node"""

    bel_nodes = request.args.getlist('node_selection[]')

    if not bel_nodes:
        abort(500, '"{}" is not a valid input for this input'.format(request.args))

    pathways = set()

    for pathway in current_app.pathme_manager.get_all_pathways():
        # Load networkX graph
        graph = from_bytes(pathway.blob)

        # Check if node is in the pathway
        for node in graph:

            if node.as_bel() not in bel_nodes:
                continue

            pathways.add(pathway)

    return render_template(
        'pathway_table.html',
        pathways=pathways,
        DATABASE_URL_DICT=DATABASE_URL_DICT,
        DATABASE_STYLE_DICT=DATABASE_STYLE_DICT
    )


@pathme.route('/pathway/overlap')
def calculate_overlap():
    """Return the overlap between different pathways in order to generate a Venn diagram."""
    pathways = process_request(request)

    if len(pathways) < 2:
        return abort(500, 'Only one pathway has been submitted!')

    pathway_data = prepare_venn_diagram_data(current_app.pathme_manager, pathways)

    processed_venn_diagram = process_overlap_for_venn_diagram(pathway_data)

    return render_template(
        'pathway_overlap.html',
        processed_venn_diagram=processed_venn_diagram,
        DATABASE_STYLE_DICT=DATABASE_STYLE_DICT
    )


@pathme.route('/pathme/viewer')
def viewer():
    """PathMe page."""
    pathways = process_request(request)

    # List of all pathway names
    pathway_id_to_name = {}
    pathway_display_names = {}
    pathway_id_to_display_name = {}
    pathway_to_resource = {}
    for pathway_id, resource in pathways.items():
        pathway = current_app.pathme_manager.get_pathway_by_id(pathway_id, resource)

        if not pathway:
            continue

        pathway_id_to_display_name[pathway_id] = pathway.display_name
        pathway_to_resource[pathway_id] = resource
        pathway_display_names[pathway.display_name] = pathway_id
        pathway_id_to_name[pathway_id] = pathway.name

    return render_template(
        'pathme_viewer.html',
        pathways=pathways,
        pathway_id_to_name=pathway_id_to_name,
        pathways_name='+'.join(
            '<a href="{}" target="_blank"> {}</a><div class="circle {}"></div>'.format(
                DATABASE_URL_DICT[pathway_to_resource[pathway_id]].format(pathway_id.strip('hsa')),
                pathway_name,
                pathway_id
            )
            for pathway_name, pathway_id in pathway_display_names.items()
        ),
        pathway_ids=list(pathways.keys()),
        DATABASE_STYLE_DICT=DATABASE_STYLE_DICT,
        DATABASE_URL_DICT=DATABASE_URL_DICT
    )


@pathme.route('/api/pathway/')
def get_network():
    """Build a graph from request and sends it in the given format."""
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    annotations = get_annotations_from_request(request)

    if annotations:
        graph = get_subgraph_by_annotations(graph, annotations)

    if COLLAPSE_TO_GENES in request.args:
        collapse_to_genes(graph)

    log.info(
        'Exporting merged graph with {} nodes and {} edges'.format(graph.number_of_nodes(), graph.number_of_edges())
    )

    graph.name = 'Merged graph from {}'.format([pathway_name for pathway_name in pathways])
    graph.version = '0.0.0'

    return export_graph(graph, request.args.get('format'))


@pathme.route('/api/tree/')
def get_network_tree():
    """Build a graph and sends the annotation ready to be rendered in the tree."""
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    annotations = get_annotations_from_request(request)

    if annotations:
        graph = get_subgraph_by_annotations(graph, annotations)

    if COLLAPSE_TO_GENES in request.args:
        collapse_to_genes(graph)

    # Return annotation in graph
    return jsonify(get_tree_annotations(graph))


@pathme.route('/api/pathway/paths')
def get_paths():
    """Return array of shortest/all paths given a source node and target node both belonging in the graph

    ---
    tags:
        - paths
        - pathway

    parameters:
      - name: pathways[]
        description: pathway resource/name pair
        required: true
        type: str

      - name: resources[]
        description: pathway resource/name pair
        required: true
        type: str

      - name: source_id
        description: The identifier of the source node
        required: true
        type: str

      - name: target_id
        description: The identifier of the target node
        required: true
        type: str

      - name: cutoff
        in: query
        description: The largest path length to keep
        required: true
        type: integer

      - name: undirected

      - name: paths_method
        in: path
        description: The method by which paths are generated - either just the shortest path, or all paths
        required: false
        default: shortest
        schema:
            type: string
            enum:
              - all
              - shortest
    """
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    # Create hash to node info
    hash_to_node = {
        node.sha512: node
        for node in graph
    }

    source_id = request.args.get('source')
    if source_id is None:
        raise IndexError('Source missing from cache: %s', source_id)

    target_id = request.args.get('target')
    if target_id is None:
        raise IndexError('target is missing from cache: %s', target_id)

    method = request.args.get(PATHS_METHOD)
    undirected = UNDIRECTED in request.args
    cutoff = request.args.get('cutoff', default=7, type=int)

    source = hash_to_node.get(source_id)
    target = hash_to_node.get(target_id)

    if source not in graph or target not in graph:
        log.info('Source/target node not in network')
        log.info('Nodes in network: %s', graph.nodes())
        abort(500, 'Source/target node not in network')

    if undirected:
        graph = graph.to_undirected()

    if method == 'all':
        paths = all_simple_paths(graph, source=source, target=target, cutoff=cutoff)
        return jsonify([
            [
                node.sha512
                for node in path
            ]
            for path in paths
        ])

    try:
        paths = shortest_path(graph, source=source, target=target)
    except NetworkXNoPath:
        log.debug('No paths between: {} and {}'.format(source, target))

        # Returns normal message if it is not a random call from graph_controller.js
        if RANDOM_PATH not in request.args:
            return 'No paths between the selected nodes'

        # In case the random node is an isolated one, returns it alone
        if not graph.neighbors(source)[0]:
            return jsonify([source])

        paths = shortest_path(graph, source=source, target=graph.neighbors(source)[0])

    return jsonify([
        node.sha512
        for node in paths
    ])


@pathme.route('/api/pathway/paths/random')
def get_random_paths():
    """Get random paths given the pathways in the graph

    ---
    tags:
        - paths
        - pathway

    parameters:
      - name: pathways[]
        description: pathway resource/name pair
        required: true
        type: str

      - name: resources[]
        description: pathway resource/name pair
        required: true
        type: str

    """
    pathways = process_request(request)

    graph = merge_pathways(pathways)

    path = get_random_path(graph)

    return jsonify([
        node.sha512
        for node in path
    ])


@pathme.route('/api/pathway/centrality')
def get_nodes_by_betweenness_centrality():
    """Get a list of nodes with the top betweenness-centrality

    ---
    tags:
        - pathway


    parameters:
      - name: pathways[]
        description: pathway resource/name pair
        required: true
        type: str

      - name: resources[]
        description: pathway resource/name pair
        required: true
        type: str

      - name: node_number
        in: path
        description: The number of top between-nodes to return
        required: true
        type: integer
    """
    node_number = request.args.get('node_number')

    if not node_number:
        abort(500, 'Missing "node_number" argument')

    try:
        node_number = int(node_number)
    except:
        abort(500, '"node_number" could not be parsed {}'.format(node_number))

    pathways = process_request(request)

    graph = merge_pathways(pathways)

    if node_number > graph.number_of_nodes():
        node_number = graph.number_of_nodes()

    bw_dict = betweenness_centrality(graph)

    return jsonify([
        node.sha512
        for node, score in sorted(bw_dict.items(), key=itemgetter(1), reverse=True)[:node_number]
    ])


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


@pathme.route('/api/database/pathways')
def api_pathways_in_database():
    """Return number of pathways in database."""
    return jsonify(current_app.pathme_manager.count_pathways())


@pathme.route('/api/node/suggestion/')
def get_node_suggestion():
    """Suggests a node

    ---
    tags:
        - node
    parameters:
      - name: q
        in: query
        description: The search term
        required: true
        type: string
    """
    q = request.args.get('q')

    if not q:
        return jsonify([])

    nodes = {
        node
        for bel, node in current_app.nodes.items()
        if q in bel
    }

    matching_nodes = [{
        "text": node.as_bel(),
        "id": node.as_bel()
    }
        for node in nodes]

    if not matching_nodes:
        return jsonify([])

    return jsonify(sorted(matching_nodes, key=lambda k: len(k["text"])))
