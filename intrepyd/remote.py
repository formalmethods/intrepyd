"""
This module runs intrepyd on an intrepid-server, the REST service of intrepyd
(https://github.com/formalmethods/intrepid-server): after use_remote(), every
Context is a RemoteContext, which has the same methods as a Context, and
turns each of them into the equivalent REST call. A script written for
intrepyd runs unchanged against the service:

    import intrepyd as ip

    ip.use_remote('http://127.0.0.1:8000')
    ctx = ip.Context()                      # a context on the service
    a = ctx.mk_input('a', ctx.mk_boolean_type())
    ...

use_local() goes back to local contexts. A RemoteContext can also be made
explicitly, with RemoteContext(url), whatever the mode.

The nets of a remote context are Net objects, named after the name the
service gives them, which is also the one in ctx.net2name; its types are the
names of the types of the REST API ('bool', 'int8', ...). Engines, traces and
simulators are objects with the methods of the local ones, and trace values
are the same strings.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from intrepyd.engine import Engine, EngineResult
from intrepyd.portfolio import ENGINES
from intrepyd.trace import Trace

_REMOTE = {'url': None}

API_PREFIX = '/api/v1/'


def use_remote(address):
    """
    Makes every Context created from now on a RemoteContext on the service
    at address, e.g. 'http://127.0.0.1:8000' or '127.0.0.1:8000'
    """
    _REMOTE['url'] = _base_url(address)


def use_local():
    """
    Makes every Context created from now on a local one again
    """
    _REMOTE['url'] = None


def get_remote():
    """
    Returns the base URL of the service that new contexts are created on, or
    None if they are local
    """
    return _REMOTE['url']


def _base_url(address):
    if '://' not in address:
        address = 'http://' + address
    address = address.rstrip('/')
    if address.endswith(API_PREFIX.rstrip('/')):
        address = address[:-len(API_PREFIX.rstrip('/'))]
    return address


class RemoteError(Exception):  # pylint: disable=too-few-public-methods
    """
    An error answered by the service
    """
    def __init__(self, method, path, status, message):
        Exception.__init__(self, f'{method} {path} answered {status}: {message}')
        self.status = status
        self.message = message


class HttpTransport:  # pylint: disable=too-few-public-methods
    """
    Sends the REST calls of a remote context to a service over HTTP
    """
    def __init__(self, url, timeout=None):
        self.url = _base_url(url)
        self.timeout = timeout

    def __call__(self, method, path, params=None, body=None):
        """
        Sends a request; returns (status, decoded JSON answer)
        """
        url = self.url + API_PREFIX + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            answer = error.read().decode('utf-8', 'replace')
            try:
                return error.code, json.loads(answer)
            except ValueError:
                return error.code, {'result': answer}


class Net:
    """
    A net of a remote context, known by the name the service gives it
    """
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Net) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f'Net({self.name!r})'

    def __str__(self):
        return self.name


# The types of the REST API, by the attribute of RemoteContext (and of
# Context) that holds them
_TYPES = {'booleantype': 'bool', 'int8type': 'int8', 'int16type': 'int16',
          'int32type': 'int32', 'int64type': 'int64', 'uint8type': 'uint8',
          'uint16type': 'uint16', 'uint32type': 'uint32', 'uint64type': 'uint64',
          'realtype': 'real', 'float16type': 'float16', 'float32type': 'float32',
          'float64type': 'float64', 'inttype': 'int'}

# The binary operators, as their REST collections
_BINARY = {'mk_and': 'ands', 'mk_or': 'ors', 'mk_xor': 'xors', 'mk_implies': 'implieses',
           'mk_iff': 'iffs', 'mk_eq': 'eqs', 'mk_leq': 'leqs', 'mk_lt': 'lts',
           'mk_geq': 'geqs', 'mk_gt': 'gts', 'mk_neq': 'neqs', 'mk_add': 'adds',
           'mk_mul': 'muls', 'mk_div': 'divs', 'mk_mod': 'mods', 'mk_sub': 'subs'}

_UNARY = {'mk_not': 'nots', 'mk_minus': 'minuses'}

_CASTS = ('int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64')


def _binary(method, collection):
    def make(self, x, y, name=None):
        return self._mk_net(f'nets/{collection}/create',  # pylint: disable=protected-access
                            {'x': x.name, 'y': y.name}, name)
    make.__name__ = method
    make.__doc__ = f'Creates the net {method[3:]}, on the service'
    return make


def _unary(method, collection):
    def make(self, x, name=None):
        return self._mk_net(f'nets/{collection}/create',  # pylint: disable=protected-access
                            {'x': x.name}, name)
    make.__name__ = method
    make.__doc__ = f'Creates the net {method[3:]}, on the service'
    return make


def _cast(typename):
    def make(self, net, name=None):
        return self._mk_net('nets/casts/create',  # pylint: disable=protected-access
                            {'x': net.name, 'type': typename}, name)
    make.__name__ = 'mk_cast_to_' + typename
    make.__doc__ = f'Casts a net to an {typename}, on the service'
    return make


def _get_type(attribute):
    def get(self):
        return getattr(self, attribute)
    kind = 'boolean' if attribute == 'booleantype' else attribute[:-len('type')]
    get.__name__ = f'mk_{kind}_type'
    get.__doc__ = f'Returns the {_TYPES[attribute]} type'
    return get


class RemoteContext:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """
    A context on an intrepid-server, with the methods of Context
    """
    def __init__(self, url=None, transport=None):
        """
        Args:
            url (str): the service, e.g. 'http://127.0.0.1:8000'; by default
                the one of use_remote()
            transport (callable): sends the REST calls instead of HTTP, as
                transport(method, path, params, body) -> (status, answer)
        """
        if transport is None:
            url = url or get_remote()
            if url is None:
                raise ValueError('No service to create the context on: '
                                 'pass its url, or call use_remote() first')
            transport = HttpTransport(url)
        self.transport = transport
        self.name = None
        self.inputs = {}
        self.outputs = {}
        self.latches = {}
        self.nets = {}
        self.net2name = {}
        self.input2type = {}
        self.namespaces = []
        self.booleantype = 'bool'
        self.int8type = 'int8'
        self.int16type = 'int16'
        self.int32type = 'int32'
        self.int64type = 'int64'
        self.uint8type = 'uint8'
        self.uint16type = 'uint16'
        self.uint32type = 'uint32'
        self.uint64type = 'uint64'
        self.realtype = 'real'
        self.float16type = 'float16'
        self.float32type = 'float32'
        self.float64type = 'float64'
        self.inttype = 'int'
        self.name = self._call('POST', 'contexts/create',
                               body={'name': 'ctx-' + uuid.uuid4().hex})

    def __del__(self):
        if getattr(self, 'name', None) is None:
            return
        try:
            self.transport('DELETE', 'contexts/delete', {'name': self.name}, None)
        except Exception:  # pylint: disable=broad-except
            # The service may be gone, or python shutting down
            pass

    def _call(self, method, path, params=None, body=None):
        """
        Sends a REST call about this context, returns its result
        """
        if self.name is not None:
            if body is not None:
                body = dict(body, context=self.name)
            else:
                params = dict(params or {}, context=self.name)
        status, answer = self.transport(method, path, params, body)
        result = answer.get('result') if isinstance(answer, dict) else answer
        if status >= 400:
            raise RemoteError(method, path, status, result)
        return result

    def _current_namespace_prefix(self):
        return ''.join(namespace + '.' for namespace in self.namespaces)

    def _register(self, canonical, name):
        """
        Records a net that the service created, as Context._register does
        """
        net = Net(canonical)
        name = canonical if name is None else self._current_namespace_prefix() + name
        self.nets[name] = net
        self.net2name.setdefault(net, canonical)
        return net

    def _mk_net(self, path, body, name):
        body = dict(body)
        if name is not None:
            body['name'] = name
        return self._register(self._call('POST', path, body=body), name)

    def push_namespace(self, name):
        """
        Pushes a namespace
        """
        self._call('PUT', 'contexts/pushnamespace', body={'name': name})
        self.namespaces.append(name)

    def pop_namespace(self):
        """
        Pops a namespace
        """
        if len(self.namespaces) == 0:
            raise Exception('Cannot pop namespace, empty list')
        self._call('PUT', 'contexts/popnamespace', body={})
        return self.namespaces.pop()

    @property
    def undef(self):
        """
        The undef net, as Context.undef
        """
        return Net(self._call('POST', 'nets/undef', body={}))

    @property
    def true(self):
        """
        The net true, as Context.true
        """
        return Net(self._call('POST', 'nets/true', body={}))

    @property
    def false(self):
        """
        The net false, as Context.false
        """
        return Net(self._call('POST', 'nets/false', body={}))

    def mk_undef(self):
        """
        Creates undef net
        """
        return self.undef

    def mk_true(self, name=None):
        """
        Creates net true
        """
        return self._mk_net('nets/true', {}, name)

    def mk_false(self, name=None):
        """
        Creates net false
        """
        return self._mk_net('nets/false', {}, name)

    def mk_number(self, value, type_, name=None):
        """
        Creates a number from a value and a type
        """
        return self._mk_net('nets/numbers/create', {'value': value, 'type': type_}, name)

    def mk_ite(self, i, t, e, name=None):
        """
        Creates the term ite(i, t, e)
        """
        return self._mk_net('nets/ites/create', {'x': i.name, 'y': t.name, 'z': e.name}, name)

    def mk_input(self, name, type_):
        """
        Creates a primary input
        """
        net = self._mk_net('inputs/create', {'type': type_}, name)
        self.inputs[name] = net
        self.input2type[net] = type_
        return net

    def mk_output(self, x, name=None):
        """
        Tag a net as output
        """
        body = {'net': x.name}
        if name is not None:
            body['name'] = name
        name = self._call('POST', 'outputs/create', body=body)
        self.nets[self._current_namespace_prefix() + name] = x
        self.net2name.setdefault(x, x.name)
        self.outputs[name] = x

    def mk_latch(self, name, type_):
        """
        Creates a latch
        """
        net = self._mk_net('latches/create', {'type': type_}, name)
        self.latches[name] = net
        return net

    def set_latch_init_next(self, latch, init, nex):
        """
        Sets the initial and next value of a latch
        """
        self._call('PUT', 'latches/initnext',
                   body={'latch': latch.name, 'init': init.name, 'next': nex.name})

    def mk_substitute(self, term, new_term, old_term):
        """
        Replaces the occurrences of oldTerm, that are found in term, with newTerm
        """
        return Net(self._call('POST', 'nets/substitutes/create',
                              body={'term': term.name, 'new': new_term.name,
                                    'old': old_term.name}))

    def mk_assumption(self, net):
        """
        Creates an assumption
        @deprecated
        """
        self._call('POST', 'engines/assumptions/create', body={'net': net.name})

    def push_assumption(self, net):
        """
        Pushes an assumption
        """
        self._call('PUT', 'engines/assumptions/push', body={'net': net.name})

    def pop_assumption(self):
        """
        Pops an assumption
        """
        self._call('PUT', 'engines/assumptions/pop', body={})

    def mk_bmc(self):
        """
        Creates a BMC engine
        """
        return RemoteBmc(self, 'bmc')

    def mk_optimizing_bmc(self):
        """
        Creates an optimizing BMC engine
        """
        return RemoteOptimizingBmc(self, 'optimizing_bmc')

    def mk_backward_reach(self):
        """
        Creates a backward reachability engine
        """
        return RemoteBackwardReach(self, 'backward_reach')

    def mk_pdr(self):
        """
        Creates an IC3/PDR engine
        """
        return RemotePdr(self, 'pdr')

    def mk_portfolio(self, engines=ENGINES, max_depth=None):
        """
        Creates a portfolio (see intrepyd.portfolio), which the service runs
        """
        return RemotePortfolio(self, engines, max_depth)

    def mk_simulator(self):
        """
        Creates a simulator
        """
        return RemoteSimulator(self)

    def mk_trace(self):
        """
        Creates an empty trace
        """
        return RemoteTrace(self, self._call('POST', 'traces/create', body={}))

    def to_string(self, net):
        """
        Returns the given net as a string, as given from the underlying smt-solver.
        """
        return self._call('GET', 'nets/tostring', params={'net': net.name})

    def get_default_value(self, type_):
        """
        Returns a default value for the given type
        """
        if type_ == self.booleantype:
            return 'F'
        if type_ in [self.float16type, self.float32type, self.float64type, self.realtype]:
            return '0.0'
        assert type_ in [self.int8type, \
                         self.int16type, \
                         self.int32type, \
                         self.uint8type, \
                         self.uint16type, \
                         self.uint32type]
        return '0'


# The methods that only differ by the type, operator or REST collection they
# are about
for _function in ([_get_type(attribute) for attribute in _TYPES] +
                  [_binary(method, collection) for method, collection in _BINARY.items()] +
                  [_unary(method, collection) for method, collection in _UNARY.items()] +
                  [_cast(typename) for typename in _CASTS]):
    _function.__qualname__ = 'RemoteContext.' + _function.__name__
    setattr(RemoteContext, _function.__name__, _function)


class RemoteEngine(Engine):  # pylint: disable=abstract-method
    """
    An engine on the service, with the methods of Engine
    """
    def __init__(self, context, kind, **options):
        Engine.__init__(self, context)
        self.context = context
        self.name = context._call(  # pylint: disable=protected-access
            'POST', 'engines/create', body=dict(options, engine=kind))

    def _call(self, method, path, params=None, body=None):
        if body is not None:
            body = dict(body, engine=self.name)
        else:
            params = dict(params or {}, engine=self.name)
        return self.context._call(method, path, params, body)  # pylint: disable=protected-access

    def add_target(self, net):
        self._call('PUT', 'engines/addtarget', body={'net': net.name})

    def add_watch(self, net):
        self._call('PUT', 'engines/watch', body={'net': net.name})

    def reach_targets(self):
        assert self.can_reach()
        return self._reach_targets({})

    def _reach_targets(self, body):
        result = self._call('PUT', 'engines/reachtargets', body=body)
        self.last_result = EngineResult[result.upper()]
        return self.last_result

    def _last_reached_targets(self):
        if self.last_result != EngineResult.REACHABLE:
            return ()
        return tuple(Net(name) for name in self._call('GET', 'engines/lastreachedtargets'))

    def get_last_reached_targets(self):
        return iter(self._last_reached_targets())

    def get_last_trace(self):
        if self.last_result != EngineResult.REACHABLE:
            raise Exception('Cannot get a trace as last result was not REACHABLE')
        return RemoteTrace(self.context, self._call('GET', 'engines/lasttrace'))

    def remove_last_reached_targets(self):
        self._call('PUT', 'engines/removelastreachedtargets', body={})

    def can_reach(self):
        return True

    def can_prove(self):
        return True

    def can_optimize(self):
        return False


class RemoteBmc(RemoteEngine):  # pylint: disable=abstract-method
    """
    A Bounded Model Checking engine on the service
    """
    def __init__(self, context, kind):
        RemoteEngine.__init__(self, context, kind)
        self._can_prove = False

    def set_current_depth(self, depth):
        """
        Sets the current depth to use for BMC
        """
        self._call('PUT', 'engines/setcurrentdepth', body={'depth': depth})

    def set_use_induction(self):
        """
        Turn on induction
        """
        self._can_prove = True
        self._call('PUT', 'engines/setuseinduction', body={})

    def set_use_attack_path_axioms(self, source, target):
        """
        Tells bmc to apply internally axioms for source and target of an attack
        """
        self._call('PUT', 'engines/setuseattackpathaxioms',
                   body={'source': source.name, 'target': target.name})

    def set_allow_targets_at_any_depth(self):
        """
        Looks for counterexamples at any depth, not just the current
        """
        self._call('PUT', 'engines/setallowtargetsatanydepth', body={})

    def can_prove(self):
        return self._can_prove


class RemoteOptimizingBmc(RemoteBmc):  # pylint: disable=abstract-method
    """
    An Optimizing Bounded Model Checking engine on the service
    """
    def can_optimize(self):
        return True


class RemoteBackwardReach(RemoteEngine):  # pylint: disable=abstract-method
    """
    A Backward Reachability engine on the service
    """


class RemotePdr(RemoteEngine):  # pylint: disable=abstract-method
    """
    An IC3/PDR engine on the service
    """


class RemotePortfolio(RemoteEngine):  # pylint: disable=abstract-method
    """
    A portfolio on the service, with the methods of Portfolio
    """
    def __init__(self, context, engines=ENGINES, max_depth=None):
        self.engines = tuple(engines)
        RemoteEngine.__init__(self, context, 'portfolio',
                              engines=list(self.engines), max_depth=max_depth)

    def reach_targets(self, timeout=None):  # pylint: disable=arguments-differ
        """
        Runs the engines until one of them answers REACHABLE or UNREACHABLE,
        and returns that answer; returns UNKNOWN if none of them does, or
        none does within timeout seconds
        """
        return self._reach_targets({} if timeout is None else {'timeout': timeout})

    def get_last_reached_targets(self):
        return self._last_reached_targets()

    def get_last_engine(self):
        """
        Returns the name of the engine that gave the last answer, or None if
        the last answer was UNKNOWN
        """
        return self._call('GET', 'engines/lastengine')

    def get_last_time(self):
        """
        Returns how long the last reach_targets() took, in seconds
        """
        return self._call('GET', 'engines/lasttime')

    def get_last_errors(self):
        """
        Returns the errors of the engines that failed in the last
        reach_targets(), as a dictionary engine -> message
        """
        return self._call('GET', 'engines/lasterrors')

    def can_prove(self):
        return any(name != 'bmc' for name in self.engines)


class RemoteSimulator:
    """
    A simulator on the service, with the methods of Simulator
    """
    def __init__(self, context):
        self.context = context
        self.name = context._call(  # pylint: disable=protected-access
            'POST', 'simulators/create', body={})

    def add_watch(self, net):
        """
        Tells the simulator about a net whose value will be reported in the simulated trace
        """
        self.context._call('PUT', 'simulators/watch',  # pylint: disable=protected-access
                           body={'simulator': self.name, 'net': net.name})

    def simulate(self, trace, depth):
        """
        Executes a simulation using the values in trace, up to the specified depth
        """
        self.context._call('PUT', 'simulators/simulate',  # pylint: disable=protected-access
                           body={'simulator': self.name, 'trace': trace.name, 'depth': depth})


class RemoteTrace(Trace):
    """
    A trace on the service, with the methods of Trace
    """
    def __init__(self, context, name):  # pylint: disable=super-init-not-called
        self.ctx = context
        self.rawtrace = None
        self.name = name

    def _call(self, method, path, params=None, body=None):
        if body is not None:
            body = dict(body, trace=self.name)
        else:
            params = dict(params or {}, trace=self.name)
        return self.ctx._call(method, path, params, body)  # pylint: disable=protected-access

    def get_max_depth(self):
        return self._call('GET', 'traces/maxdepth')

    def get_value(self, net, depth):
        return self._call('GET', 'traces/value', params={'net': net.name, 'depth': depth})

    def set_value(self, net, depth, value):
        self._call('PUT', 'traces/setvalue', body={'net': net.name, 'depth': depth,
                                                    'value': value})

    def get_as_net_dictionary(self, net2name=None):
        values = {Net(name): steps for name, steps in self._call('GET', 'traces/values').items()}
        if net2name is None:
            return values
        return {net2name[net]: steps for net, steps in values.items()}

    def get_as_depth_dictionary(self):
        values = list(self.get_as_net_dictionary().values())
        return {depth: [steps[depth] for steps in values]
                for depth in range(self.get_max_depth())}
