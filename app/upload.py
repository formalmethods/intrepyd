"""
Implementation of REST API for upload
"""

from io import TextIOWrapper
from flask import Blueprint, request
from intrepyd.parser import ParseError, Parser
from .contexts import contexts

ur = Blueprint('upload', __name__)

@ur.route('', methods=['POST'])
def upload():
    """
    Uploads and parses a file in intrepid syntax
    """
    file = request.files['file']
    try:
        parser = Parser()
        with TextIOWrapper(file.stream, encoding='utf-8') as stream:
            ctx = parser.parse_stream(stream)
        name = '__ctx{}'.format(len(contexts))
        contexts[name] = {'context': ctx,
                          'inputs': ctx.inputs,
                          'nets': ctx.nets,
                          'latches': ctx.latches,
                          'engines': {},
                          'traces': {},
                          'simulators': {}}
        return {'result': {'ctx': name}}, 201
    except ParseError as err:
        return {'result': err.message()}, 400
    except:
        return {'result': 'uncaught exception'}, 400
