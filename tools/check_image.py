#!/usr/bin/env python3
"""
Checks a running container of the REST service, for the release workflow and
'make -f Makefile.docker docker_test': waits for it to answer, then runs a
short session through the REST API, which exercises the intrepid library
inside the image, with BMC, PDR and an uploaded model.

    check_image.py [BASE_URL]      (default: http://127.0.0.1:8000)
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

TIMEOUT = 60


def request(base, method, path, body=None, files=None):
    """Sends a request, returns the decoded JSON answer"""
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif files is not None:
        boundary = uuid.uuid4().hex
        parts = []
        for field, (filename, content) in files.items():
            parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; '
                          'filename="%s"\r\nContent-Type: text/plain\r\n\r\n'
                          % (boundary, field, filename)).encode('utf-8'))
            parts.append(content.encode('utf-8') + b'\r\n')
        parts.append(('--%s--\r\n' % boundary).encode('utf-8'))
        data = b''.join(parts)
        headers['Content-Type'] = 'multipart/form-data; boundary=%s' % boundary
    req = urllib.request.Request(base + '/api/v1/' + path, data=data,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit('Error: %s %s answered %s: %s'
                 % (method, path, error.code, error.read().decode('utf-8', 'replace')))


def wait_until_up(base):
    deadline = time.monotonic() + TIMEOUT
    while True:
        try:
            with urllib.request.urlopen(base + '/api/v1/contexts', timeout=5):
                return
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            if time.monotonic() > deadline:
                sys.exit('Error: %s does not answer after %d seconds: %s'
                         % (base, TIMEOUT, error))
            time.sleep(1)


def expect(what, actual, expected):
    if actual != expected:
        sys.exit('Error: %s is %r, expected %r' % (what, actual, expected))


def reach(base, context, engine_kind, target, depth=None):
    engine = request(base, 'POST', 'engines/create',
                     {'context': context, 'engine': engine_kind})['result']
    request(base, 'PUT', 'engines/addtarget',
            {'context': context, 'engine': engine, 'net': target})
    if depth is not None:
        request(base, 'PUT', 'engines/setcurrentdepth',
                {'context': context, 'engine': engine, 'depth': depth})
    result = request(base, 'PUT', 'engines/reachtargets',
                     {'context': context, 'engine': engine})['result']
    return engine, result


def check_session(base):
    # a AND b, built net by net, is reachable at depth 0
    context = request(base, 'POST', 'contexts/create', {'name': 'check'})['result']
    a = request(base, 'POST', 'inputs/create', {'context': context, 'type': 'bool'})['result']
    b = request(base, 'POST', 'inputs/create', {'context': context, 'type': 'bool'})['result']
    gate = request(base, 'POST', 'nets/ands/create',
                   {'context': context, 'x': a, 'y': b})['result']
    engine, result = reach(base, context, 'bmc', gate, depth=0)
    expect('the bmc result', result, 'reachable')
    trace = request(base, 'GET', 'engines/lasttrace?context=%s&engine=%s'
                    % (context, engine))['result']
    values = request(base, 'GET', 'traces/values?context=%s&trace=%s'
                     % (context, trace))['result']
    expect('the counterexample', values, {a: ['T'], b: ['T']})
    _, result = reach(base, context, 'pdr', gate)
    expect('the pdr result', result, 'reachable')

    # A latch that stays false, uploaded: never true, which PDR proves
    model = 'l1 = latch bool\nset_latch_init_next l1 false l1\n'
    uploaded = request(base, 'POST', 'upload', files={'file': ('model.txt', model)})
    context = uploaded['result']['ctx']
    _, result = reach(base, context, 'pdr', 'l1')
    expect('the pdr result on the uploaded model', result, 'unreachable')


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__.strip().split('\n\n')[1])
    base = (sys.argv[1] if len(sys.argv) == 2 else 'http://127.0.0.1:8000').rstrip('/')
    wait_until_up(base)
    check_session(base)
    print('# The REST service at %s works' % base)


if __name__ == '__main__':
    main()
