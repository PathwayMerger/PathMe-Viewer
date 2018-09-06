# -*- coding: utf-8 -*-

"""This module contains the PathMe Flask Application application."""

import logging
import os
import time

from flasgger import Swagger
from flask import Flask
from flask_admin import Admin
from flask_bootstrap import Bootstrap
from flask_security import Security
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from ..constants import DEFAULT_CACHE_CONNECTION
from ..manager import Manager
from ..models import Base, Pathway
from ..web.views import redirect, pathme, PathwayView

log = logging.getLogger(__name__)

bootstrap = Bootstrap()
security = Security()
swagger = Swagger()


class PathMeSQLAlchemy(SQLAlchemy):
    """PathMe"""

    def init_app(self, app):
        """Overwrite init app method."""
        super().init_app(app)

        self.manager = Manager(engine=self.engine, session=self.session)


def create_app(template_folder=None, static_folder=None):
    """Create the Flask application.

    :type template_folder: Optional[str]
    :type static_folder: Optional[str]
    :rtype: flask.Flask
    """
    t = time.time()

    app = Flask(
        __name__,
        template_folder=(template_folder or '../templates'),
        static_folder=(static_folder or '../static'),
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = DEFAULT_CACHE_CONNECTION
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.update(
        SECURITY_REGISTERABLE=True,
        SECURITY_CONFIRMABLE=False,
        SECURITY_SEND_REGISTER_EMAIL=False,
        SECURITY_RECOVERABLE=True,
        #: What hash algorithm should we use for passwords
        SECURITY_PASSWORD_HASH='pbkdf2_sha512',
        #: What salt should we use to hash passwords? DEFINITELY CHANGE THIS
        SECURITY_PASSWORD_SALT=os.environ.get('PATHME_SECURITY_PASSWORD_SALT', 'pathme_not_default_salt1234567890')
    )

    app.secret_key = os.urandom(24)

    admin = Admin(app, template_mode='bootstrap3')

    CSRFProtect(app)
    bootstrap.init_app(app)
    db = PathMeSQLAlchemy(app)

    with app.app_context():
        Base.metadata.bind = db.engine
        Base.query = db.session.query_property()

        try:
            db.create_all()
        except Exception:
            log.exception('Failed to create all')

    app.pathme_manager = db.manager

    app.register_blueprint(pathme)
    app.register_blueprint(redirect)

    admin.add_view(PathwayView(Pathway, app.pathme_manager.session))

    log.info('Done building %s in %.2f seconds', app, time.time() - t)
    return app


if __name__ == '__main__':
    app_ = create_app()
    app_.run(debug=True, host='0.0.0.0', port=5000)
