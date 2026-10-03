"""
Entry point for REST API service
"""

from flask import Flask
from app.contexts import cr, contexts as ctxs
from app.inputs import ir
from app.latches import lr
from app.nets import nr
from app.engines import er
from app.traces import tr
from app.simulators import sr
from app.debug import dr
from app.upload import ur

PREFIX = '/api/v1/'

def create_app():
    app = Flask(__name__)
    app.register_blueprint(cr, url_prefix=PREFIX + 'contexts')
    app.register_blueprint(ir, url_prefix=PREFIX + 'inputs')
    app.register_blueprint(lr, url_prefix=PREFIX + 'latches')
    app.register_blueprint(nr, url_prefix=PREFIX + 'nets')
    app.register_blueprint(er, url_prefix=PREFIX + 'engines')
    app.register_blueprint(tr, url_prefix=PREFIX + 'traces')
    app.register_blueprint(sr, url_prefix=PREFIX + 'simulators')
    app.register_blueprint(dr, url_prefix=PREFIX + 'debug')
    app.register_blueprint(ur, url_prefix=PREFIX + 'upload')
    app.config['UPLOAD_FOLDER'] = '/tmp'
    app.config['MAX_CONTENT_PATH'] = gigabytes_in_bytes(2)
    return app

def gigabytes_in_bytes(n):
    return n * 1024 * 1024 * 1024

def destroy_app():
    ctxs.clear()

app = create_app()
