# -*- coding: utf-8 -*-

"""This module contains the methods used to deal with BELGraphs."""

import logging
from itertools import combinations
from operator import methodcaller

from flask import abort, Response, jsonify, send_file
from flask import current_app
from pybel import collapse_to_genes, to_bel_lines, to_graphml, to_bytes, to_csv, union
from pybel.constants import *
from pybel.dsl import BaseAbundance
from pybel.io import from_bytes
from pybel.struct import add_annotation_value
from pybel.struct.summary import get_annotation_values_by_annotation
from six import BytesIO, StringIO

from pathme_viewer.constants import BLACK_LIST, PATHWAYS_ARGUMENT, RESOURCES_ARGUMENT
from pybel_tools.summary.contradictions import relation_set_has_contradictions

log = logging.getLogger(__name__)


def throw_parameter_error(parameter):
    """Return 500 error.

    :param str parameter:
    :return: HTTP error
    """
    abort(500, '"{}" argument is missing in the request'.format(parameter))


def add_annotation_key(graph):
    """Add annotation key in data (in place operation).

    :param pybel.BELGraph graph: BEL Graph
    """
    for u, v, k in graph.edges(keys=True):
        if ANNOTATIONS not in graph[u][v][k]:
            graph[u][v][k][ANNOTATIONS] = {}


def process_request(request):
    """Process request and return it as a dict[pathway ids,resources].

    :param flask.request request: http request
    :rtype: dict
    """
    pathways_list = request.args.getlist(PATHWAYS_ARGUMENT)
    resources_list = request.args.getlist(RESOURCES_ARGUMENT)

    if not resources_list:
        throw_parameter_error(RESOURCES_ARGUMENT)

    if not pathways_list:
        throw_parameter_error(PATHWAYS_ARGUMENT)

    return {
        pathway_id: resource
        for pathway_id, resource in zip(pathways_list, resources_list)
    }


def get_annotations_from_request(request):
    """Return dictionary with annotations.

    :param flask.request request: http request
    :rtype: dict
    """
    annotations = {}
    for arguments in request.args.keys():

        if arguments in BLACK_LIST:
            continue

        annotations[arguments] = request.args.getlist(arguments)

    return annotations


def merge_pathways(pathways):
    """Return merged graphs from pathways in the request.

    :param dict pathways: pathways to be merged
    :rtype: Optional[pybel.BELGraph]
    """
    networks = []

    for name, resource in pathways.items():

        pathway = current_app.pathme_manager.get_pathway_by_id(name, resource)

        if not pathway:
            abort(
                500,
                'Pathway "{}" in resource "{}" was not found in the database. '
                'Please check that you have used correctly the autocompletion form.'.format(
                    name, resource)
            )

        # Loads the BELGraph and adds annotations to track provenance later
        graph = from_bytes(pathway.blob)

        graph.annotation_list['Database'] = {'kegg', 'reactome', 'wikipathways'}
        graph.annotation_pattern['PathwayID'] = '.*'
        graph.annotation_pattern['Pathway name'] = '.*'
        graph.annotation_list['Interesting edge'] = {'Contradicts', 'May contradict'}
        add_annotation_key(graph)

        add_annotation_value(graph, 'Pathway name', pathway.name)
        add_annotation_value(graph, 'Database', pathway.resource_name)
        add_annotation_value(graph, 'PathwayID', pathway.pathway_id)

        log.debug('Adding graph {} {}:with {} nodes and {} edges'.format(
            name, resource, graph.number_of_nodes(), graph.number_of_edges())
        )

        networks.append(graph)

    if not networks:
        abort(
            500,
            'Any pathway was requested. Please select at least one pathway.'
        )

    graph = union(networks)
    graph.name = 'Merged graph from {}'.format([graph.name for graph in networks])
    graph.version = '0.0.0'

    contradicting_edges = get_contradiction_summary(graph)

    for u, v, _ in contradicting_edges:
        label_graph_edges(graph, u, v, 'Interesting edge', 'Contradicts')

    return graph


def to_json_custom(graph, _id='id', source='source', target='target'):
    """Prepares JSON for the biological network explorer

    :type graph: pybel.BELGraph
    :param str _id: The key to use for the identifier of a node, which is calculated with an enumeration
    :param str source: The key to use for the source node
    :param str target: The key to use for the target node
    :rtype: dict
    """
    result = {}

    mapping = {}

    result['nodes'] = []
    for i, node in enumerate(sorted(graph, key=methodcaller('as_bel'))):
        nd = node.copy()
        nd[_id] = node.sha512
        nd['bel'] = node.as_bel()
        if VARIANTS in nd or FUSION in nd or MEMBERS in nd:
            nd['cname'] = nd['bel']
        result['nodes'].append(nd)
        mapping[node] = i

    edge_set = set()

    rr = {}

    for u, v, data in graph.edges(data=True):

        if data[RELATION] in TWO_WAY_RELATIONS and (u, v) != tuple(sorted((u, v), key=methodcaller('as_bel'))):
            continue  # don't keep two way edges twice

        entry_code = u, v

        if entry_code not in edge_set:  # Avoids duplicate sending multiple edges between nodes with same relation
            rr[entry_code] = {
                source: mapping[u],
                target: mapping[v],
                'contexts': []
            }

            edge_set.add(entry_code)

        payload = {
            'bel': graph.edge_to_bel(u, v, data)
        }
        payload.update(data)

        if data[RELATION] in CAUSAL_INCREASE_RELATIONS:
            rr[entry_code][RELATION] = INCREASES

        elif data[RELATION] in CAUSAL_DECREASE_RELATIONS:
            rr[entry_code][RELATION] = DECREASES

        rr[entry_code]['contexts'].append(payload)

    result['links'] = list(rr.values())

    return result


def export_graph(graph, format=None):
    """Convert PyBEL graph to a different format.

    :param PyBEL graph graph: graph
    :param format: desire format
    :return: graph representation in different format
    """
    if format is None or format == 'json':
        data = to_json_custom(graph)
        return jsonify(data)

    elif format == 'bytes':
        data = BytesIO(to_bytes(graph))
        return send_file(
            data,
            mimetype='application/octet-stream',
            as_attachment=True,
            attachment_filename='graph.gpickle'
        )

    elif format == 'bel':
        data = '\n'.join(to_bel_lines(graph))
        return Response(data, mimetype='text/plain')

    elif format == 'graphml':
        bio = BytesIO()
        to_graphml(graph, bio)
        bio.seek(0)
        return send_file(
            bio,
            mimetype='text/xml',
            attachment_filename='graph.graphml',
            as_attachment=True
        )

    elif format == 'csv':
        bio = StringIO()
        to_csv(graph, bio)
        bio.seek(0)
        data = BytesIO(bio.read().encode('utf-8'))
        return send_file(
            data,
            mimetype="text/tab-separated-values",
            attachment_filename="graph.tsv",
            as_attachment=True
        )

    abort(500, '{} is not a valid format'.format(format))


def get_tree_annotations(graph):
    """Build tree structure with annotation for a given graph.

    :param pybel.BELGraph graph: A BEL Graph
    :return: The JSON structure necessary for building the tree box
    :rtype: list[dict]
    """
    annotations = get_annotation_values_by_annotation(graph)

    return [
        {
            'text': annotation,
            'children': [{'text': value} for value in sorted(values)]
        }
        for annotation, values in sorted(annotations.items())
    ]


def label_graph_edges(graph, u, v, annotation, value):
    """Label edges between two nodes with an annotation and a value.

    :param pybel.BELGraph graph:
    :param u: subject node
    :param v: object node
    :param str annotation: annotation to be labelled
    :param str value: value to be labelled
    """
    if annotation not in graph.defined_annotation_keywords:
        raise ValueError('annotation not defined: {}'.format(annotation))

    if not graph.has_edge(u, v):
        raise ValueError('edge does not exists')

    # Iterate over all edges between u and v
    for k, data in graph[u][v].items():

        # Add annotation key in data if not exists
        if ANNOTATIONS not in data:
            graph[u][v][k][ANNOTATIONS] = {}

        if annotation not in data[ANNOTATIONS]:
            graph[u][v][k][ANNOTATIONS] = {annotation: {}}

        graph[u][v][k][ANNOTATIONS][annotation][value] = True


def relation_set_has_differences(relations):
    """Return if the set of relations contains differences.

    :param set[str] relations: A set of relations
    :rtype: bool
    """
    has_causal = any(relation in CAUSAL_RELATIONS for relation in relations)
    has_unspecific_event = any(relation in {ASSOCIATION} for relation in relations)
    return 1 < sum([has_causal, has_unspecific_event])


def get_contradiction_summary(graph):
    """Yield triplets of (source node, target node, set of relations) for (source node, target node) pairs
    that have multiple, contradictory relations.

    :param pybel.BELGraph graph: A BEL graph
    :rtype: iter[tuple]
    """
    for u, v in set(graph.edges()):
        relations = {data[RELATION] for data in graph[u][v].values()}
        if relation_set_has_contradictions(relations):
            yield u, v, relations


def get_pathway_nodes(pathway):
    """Return single nodes in pathway.

    :param pathme_viewer.models.Pathway pathway: pathway entry
    :return: BaseAbundance nodes
    :rtype: list[pybel.dsl.BaseAbundance]
    """
    # Loads the BELGraph
    graph = from_bytes(pathway.blob)

    collapse_to_genes(graph)

    # Return BaseAbundace BEL nodes
    return {
        node.as_bel()
        for node in graph
        if isinstance(node, BaseAbundance)
    }


def prepare_venn_diagram_data(manager, pathways):
    """Prepare Venn Diagram data.

    :param pathme_viewer.manager.Manager manager: Manager
    :param dict[str,str] pathways: pathway id resource dict
    :rtype: dict
    """
    pathway_data = {}
    for pathway_id, resource in pathways.items():
        # Get pathway from DB
        pathway = manager.get_pathway_by_id(pathway_id, resource)

        # Confirm that pathway exists
        if not pathway:
            abort(
                500,
                'Pathway "{}" in resource "{}" was not found in the database. '
                'Please check that you have used correctly the autocompletion form.'.format(
                    pathway_id, resource)
            )
        # Get pathway nodes
        nodes = get_pathway_nodes(pathway)

        pathway_data[pathway.name] = nodes

    return pathway_data


def process_overlap_for_venn_diagram(pathways_nodes, skip_gene_set_info=False):
    """Calculate gene sets overlaps and process the structure to render venn diagram -> https://github.com/benfred/venn.js/.

    :param dict[str,set] pathways_nodes: pathway to bel nodes dictionary
    :param bool skip_gene_set_info: include gene set overlap data
    :return: list[dict]
    """

    # Creates future js array with gene sets' lengths
    overlaps_venn_diagram = []

    pathway_to_index = {}
    index = 0

    for name, bel_nodes in pathways_nodes.items():

        # Only minimum info is returned
        if skip_gene_set_info:
            overlaps_venn_diagram.append(
                {'sets': [index], 'size': len(bel_nodes), 'label': name.upper()}
            )
        # Returns gene set overlap/intersection information as well
        else:
            overlaps_venn_diagram.append(
                {'sets': [index], 'size': len(bel_nodes), 'label': name, 'bel_nodes': list(bel_nodes)}
            )

        pathway_to_index[name] = index

        index += 1

    # Perform intersection calculations
    for (set_1_name, set_1_values), (set_2_name, set_2_values) in combinations(pathways_nodes.items(), r=2):
        # Only minimum info is returned
        if skip_gene_set_info:
            overlaps_venn_diagram.append(
                {
                    'sets': [pathway_to_index[set_1_name], pathway_to_index[set_2_name]],
                    'size': len(set_1_values.intersection(set_2_values)),
                }
            )
        # Returns gene set overlap/intersection information as well
        else:
            overlaps_venn_diagram.append(
                {
                    'sets': [pathway_to_index[set_1_name], pathway_to_index[set_2_name]],
                    'size': len(set_1_values.intersection(set_2_values)),
                    'bel_nodes': list(set_1_values.intersection(set_2_values)),
                    'intersection': set_1_name + ' &#8745 ' + set_2_name
                }
            )

    return overlaps_venn_diagram
