# -*- coding: utf-8 -*-

"""Tests for functions for identifying contradictions in pathways."""

import unittest

from pybel import BELGraph
from pybel.testing.utils import n
from pybel.dsl import protein
from pathme_viewer.graph_utils import get_contradiction_summary
from pybel.constants import CAUSES_NO_CHANGE

test_namespace_url = n()
test_annotation_url = n()
citation, evidence = n(), n()
a, b, c, d, e = [protein(namespace='test', name=str(i)) for i in range(5)]


class TestAnnotation(unittest.TestCase):
    """Tests for getting sub-graphs by annotation."""

    def setUp(self):
        """Set up the test case with a pre-populated BEL graph."""

        self.graph = BELGraph()

        self.graph.namespace_url['test'] = test_namespace_url
        self.graph.annotation_url['subgraph'] = test_annotation_url

        # A increases/decreases B.
        self.graph.add_increases(a, b, citation=citation, evidence=evidence, annotations={'subgraph': {'1', '2'}})
        self.graph.add_decreases(a, b, citation=citation, evidence=evidence, annotations={'subgraph': {'1'}})

        # B increases association with C.
        self.graph.add_increases(b, c, citation=citation, evidence=evidence, annotations={'subgraph': {'1', '2'}})
        self.graph.add_association(b, c, citation=citation, evidence=evidence, annotations={'subgraph': {'2'}})

        # C increases D
        self.graph.add_increases(c, d, citation=citation, evidence=evidence)

        self.graph.add_increases(d, e, citation=citation, evidence=evidence, annotations={'subgraph': {'1', '2'}})
        self.graph.add_qualified_edge(
            d, e, relation=CAUSES_NO_CHANGE, evidence=evidence, citation=citation,
            annotations={'subgraph': {'1', '2'}})

    def test_contradictions_finder(self):
        """Simple test to find contradictions."""
        contradictory_edges = get_contradiction_summary(self.graph)

        contradictions = [
            (protein(namespace='test', name='0'), protein(namespace='test', name='1'), {'decreases', 'increases'}),
            (protein(namespace='test', name='3'), protein(namespace='test', name='4'), {'causesNoChange', 'increases'})
        ]

        for edge in contradictory_edges:
            self.assertIn(edge, contradictions)

