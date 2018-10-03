# -*- coding: utf-8 -*-

"""This module contains the PathMe database manager."""

import logging

from bio2bel.utils import get_connection
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import scoped_session, sessionmaker

from .constants import MODULE_NAME
from .models import Base, Pathway

__all__ = [
    'Manager'
]

log = logging.getLogger(__name__)


class Manager(object):
    """Database manager."""

    def __init__(self, engine, session):
        """Init PathMe manager."""
        self.engine = engine
        self.session = session
        self.create_all()

    @staticmethod
    def from_connection(connection=None):
        connection = get_connection(MODULE_NAME, connection)
        engine = create_engine(connection)
        session_maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        session = scoped_session(session_maker)
        return Manager(engine, session)

    def create_all(self, check_first=True):
        """Create tables for PathMe."""
        Base.metadata.create_all(self.engine, checkfirst=check_first)

    def drop_all(self, check_first=True):
        """Drop all tables for PathMe."""
        Base.metadata.drop_all(self.engine, checkfirst=check_first)

    """Query methods"""

    def count_pathways(self):
        """Count the pathways in the database.

        :rtype: int
        """
        return self.session.query(Pathway).count()

    def count_pathways_by_resource(self):
        """Count the pathways in the database grouping by resource.

        :rtype: int
        """
        return self.session.query(
            Pathway.resource_name, func.count(Pathway.resource_name)
        ).group_by(Pathway.resource_name).all()

    def get_all_pathways(self):
        """Get all pathways in the database.

        :rtype: list[Pathway]
        """
        return self.session.query(Pathway).all()

    def get_pathway_by_id(self, pathway_id, resource_name):
        """Get pathway by canonical identifier.

        :param str pathway_id: pathway identifier
        :param str resource_name: name of the database
        :rtype: Optional[Pathway]
        """
        condition = and_(Pathway.pathway_id == pathway_id, Pathway.resource_name == resource_name)
        return self.session.query(Pathway).filter(condition).one_or_none()

    def get_pathway_by_name(self, pathway_name, resource_name):
        """Get pathway by name.

        :param str pathway_name: pathway identifier
        :param str resource_name: name of the database
        :rtype: Optional[Pathway]
        """
        condition = and_(Pathway.name == pathway_name, Pathway.resource_name == resource_name)
        return self.session.query(Pathway).filter(condition).one_or_none()

    def get_pathways_from_resource(self, resource_name):
        """Get pathways from a given database.

        :param str resource_name: name of the database
        :rtype: Optional[list[Pathway]]
        """
        return self.session.query(Pathway).filter(Pathway.resource_name == resource_name).all()

    def create_pathway(self, pathway_dict):
        """Create pathway.

        :param dict pathway_dict: pathway identifier
        :rtype: Pathway
        """
        pathway = Pathway(**pathway_dict)

        self.session.add(pathway)
        self.session.commit()

        return pathway

    def delete_pathway(self, pathway_id, resource_name):
        """Delete a pathway.

        :param str pathway_id: pathway identifier
        :param str resource_name: name of the database
        :rtype: bool
        """
        pathway = self.get_pathway_by_id(pathway_id, resource_name)

        if pathway:
            self.session.delete(pathway)
            self.session.commit()
            return True

        return False

    def delete_all_pathways(self):
        """Delete all the pathways."""
        self.session.query(Pathway).delete()
        self.session.commit()

    def delete_pathways_from_resource(self, resource_name):
        """Delete pathways from a given database.

        :param str resource_name: name of the database
        :rtype: bool
        """
        pathways_in_resource = self.session.query(Pathway).filter(Pathway.resource_name == resource_name)

        if not pathways_in_resource:
            return False

        pathways_in_resource.delete()
        self.session.commit()

        return True

    def get_or_create_pathway(self, pathway_dict):
        """Get or create pathway.

        :param dict pathway_dict: pathway info
        :rtype: Pathway
        """
        pathway = self.get_pathway_by_id(pathway_dict['pathway_id'], pathway_dict['resource_name'])

        if pathway is None:
            pathway = self.create_pathway(pathway_dict)

        return pathway

    def query_pathway_by_name(self, query, resource, limit=None):
        """Return all pathways having the query in their names.

        :param str query: query string
        :param Optional[int] limit: limit result query
        :rtype: list[Pathway]
        """
        q = self.session.query(Pathway).filter(Pathway.name.contains(query))

        if limit:
            q = q.limit(limit)

        return q.all()

    def query_pathway_by_name_and_resource(self, query, resource_name, limit=None):
        """Return all pathways having the query in their names.

        :param str query: query string
        :param str resource_name: database name
        :param Optional[int] limit: limit result query
        :rtype: list[Pathway]
        """
        condition = and_(Pathway.name.contains(query), Pathway.resource_name == resource_name)
        q = self.session.query(Pathway).filter(condition)

        if limit:
            q = q.limit(limit)

        return q.all()
