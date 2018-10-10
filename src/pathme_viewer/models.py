# -*- coding: utf-8 -*-

"""PathMe models."""

import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base

from pybel import from_bytes
from .constants import MODULE_NAME, DATABASE_STYLE_DICT

LONGBLOB = 4294967295

Base = declarative_base()

TABLE_PREFIX = MODULE_NAME

NETWORK_TABLE_NAME = 'pathme_network'


class Pathway(Base):
    """Represents a pathway network  in BEL format harmonized by ComPath"""
    __tablename__ = NETWORK_TABLE_NAME

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False, index=True, doc='Pathway name')
    resource_name = Column(String(255), nullable=False, index=True, doc='Database of origin')
    pathway_id = Column(String(255), nullable=False, index=True, doc='Pathway identifier in database of origin')

    number_of_nodes = Column(Integer(), doc='Number of nodes')
    number_of_edges = Column(Integer(), doc='Number of edges')

    version = Column(String(16), nullable=False, doc='Version of the BEL file')
    authors = Column(Text, nullable=True, doc='Authors of the underlying BEL file')
    contact = Column(String(255), nullable=True, doc='Contact email from the underlying pathway')
    description = Column(Text, nullable=True, doc='Descriptive text from the pathway')

    pybel_version = Column(String(16), nullable=False, doc='Version of PyBEL')
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    blob = Column(LargeBinary(LONGBLOB), doc='A pickled version of this pathway')

    def __str__(self):
        """Return pathway name."""
        return '{} ({})'.format(
            self.name,
            DATABASE_STYLE_DICT.get(self.resource_name, self.resource_name)
        )

    @property
    def display_name(self):
        """Return pathway name."""
        return '{} ({})'.format(
            self.name,
            DATABASE_STYLE_DICT.get(self.resource_name, self.resource_name)
        )

    def as_bel(self):
        """Get this network and loads it into a :class:`BELGraph`.

        :rtype: pybel.BELGraph
        """
        return from_bytes(self.blob)
