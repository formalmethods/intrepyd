import intrepyd
import intrepyd.engine
import intrepyd.portfolio
import intrepyd.simulator
import intrepyd.trace
import unittest
from intrepyd.engine import EngineResult
from intrepyd.remote import (Net, RemoteBackwardReach, RemoteBmc, RemoteContext,
                             RemoteError, RemoteOptimizingBmc, RemotePdr,
                             RemotePortfolio, RemoteSimulator, RemoteTrace)


def public(obj):
    return {name for name in dir(obj) if not name.startswith('_')}


class FakeService:
    """
    A transport that records the REST calls, and answers each from a list of
    canned answers, by path
    """
    def __init__(self, answers=None):
        self.calls = []
        self.answers = answers or {}

    def __call__(self, method, path, params, body):
        self.calls.append((method, path, params, body))
        if path == 'contexts/create':
            return 201, {'result': body['name']}
        answers = self.answers.get(path)
        if not answers:
            return 200, {'result': 'ok'}
        return answers.pop(0)


class TestRemote(unittest.TestCase):

    def tearDown(self):
        intrepyd.use_local()

    def test_same_api_as_local(self):
        pairs = [(intrepyd.context.Context, RemoteContext),
                 (intrepyd.engine.Bmc, RemoteBmc),
                 (intrepyd.engine.OptimizingBmc, RemoteOptimizingBmc),
                 (intrepyd.engine.BackwardReach, RemoteBackwardReach),
                 (intrepyd.engine.Pdr, RemotePdr),
                 (intrepyd.portfolio.Portfolio, RemotePortfolio),
                 (intrepyd.simulator.Simulator, RemoteSimulator),
                 (intrepyd.trace.Trace, RemoteTrace)]
        for local, remote in pairs:
            self.assertEqual(set(), public(local) - public(remote), remote.__name__)
        attributes = public(intrepyd.Context()) - public(intrepyd.context.Context)
        attributes -= {'ctx', 'recipe'}
        remote = RemoteContext(transport=FakeService())
        self.assertEqual(set(), attributes - public(remote))

    def test_use_remote(self):
        self.assertIsInstance(intrepyd.Context(), intrepyd.context.Context)
        intrepyd.use_remote('127.0.0.1:8000')
        self.assertEqual('http://127.0.0.1:8000', intrepyd.remote.get_remote())
        intrepyd.use_remote('https://example.org/api/v1/')
        self.assertEqual('https://example.org', intrepyd.remote.get_remote())
        intrepyd.use_local()
        self.assertIsNone(intrepyd.remote.get_remote())
        self.assertIsInstance(intrepyd.Context(), intrepyd.context.Context)

    def test_no_service(self):
        with self.assertRaises(ValueError):
            RemoteContext()

    def test_nets(self):
        service = FakeService({'inputs/create': [(201, {'result': 'a'}), (201, {'result': 'b'})],
                               'nets/ands/create': [(201, {'result': '__n12'})],
                               'nets/numbers/create': [(201, {'result': 'one'})],
                               'outputs/create': [(201, {'result': '__o12'})]})
        ctx = RemoteContext(transport=service)
        bool_t = ctx.mk_boolean_type()
        self.assertEqual('bool', bool_t)
        a = ctx.mk_input('a', bool_t)
        b = ctx.mk_input('b', bool_t)
        c = ctx.mk_and(a, b)
        one = ctx.mk_number('1', ctx.mk_int8_type(), name='one')
        ctx.mk_output(c)
        self.assertEqual(Net('__n12'), c)
        self.assertEqual({'a': a, 'b': b}, ctx.inputs)
        self.assertEqual({'__o12': c}, ctx.outputs)
        self.assertEqual({'a': a, 'b': b, '__n12': c, 'one': one, '__o12': c}, ctx.nets)
        self.assertEqual('__n12', ctx.net2name[c])
        self.assertEqual(bool_t, ctx.input2type[a])
        context = ctx.name
        self.assertEqual([
            ('POST', 'contexts/create', None, {'name': context}),
            ('POST', 'inputs/create', None, {'type': 'bool', 'name': 'a', 'context': context}),
            ('POST', 'inputs/create', None, {'type': 'bool', 'name': 'b', 'context': context}),
            ('POST', 'nets/ands/create', None, {'x': 'a', 'y': 'b', 'context': context}),
            ('POST', 'nets/numbers/create', None,
             {'value': '1', 'type': 'int8', 'name': 'one', 'context': context}),
            ('POST', 'outputs/create', None, {'net': '__n12', 'context': context}),
        ], service.calls)
        del ctx
        self.assertEqual(('DELETE', 'contexts/delete', {'name': context}, None),
                         service.calls[-1])

    def test_namespaces(self):
        service = FakeService({'inputs/create': [(201, {'result': 'A.a'})],
                               'contexts/popnamespace': [(200, {'result': 'A'})]})
        ctx = RemoteContext(transport=service)
        ctx.push_namespace('A')
        a = ctx.mk_input('a', ctx.mk_boolean_type())
        self.assertEqual('A', ctx.pop_namespace())
        self.assertEqual({'a': a}, ctx.inputs)
        self.assertEqual({'A.a': a}, ctx.nets)
        with self.assertRaises(Exception):
            ctx.pop_namespace()

    def test_bmc(self):
        service = FakeService({'engines/create': [(201, {'result': 'e0'})],
                               'engines/reachtargets': [(200, {'result': 'unknown'}),
                                                        (200, {'result': 'reachable'})],
                               'engines/lastreachedtargets': [(200, {'result': ['t']})],
                               'engines/lasttrace': [(200, {'result': 't0'})],
                               'traces/values': [(200, {'result': {'t': ['F', 'T']}})]})
        ctx = RemoteContext(transport=service)
        target = Net('t')
        bmc = ctx.mk_bmc()
        bmc.add_target(target)
        self.assertFalse(bmc.can_prove())
        self.assertEqual(EngineResult.UNKNOWN, bmc.reach_targets())
        self.assertEqual((), tuple(bmc.get_last_reached_targets()))
        with self.assertRaises(Exception):
            bmc.get_last_trace()
        self.assertEqual(EngineResult.REACHABLE, bmc.reach_targets())
        self.assertEqual(target, next(bmc.get_last_reached_targets()))
        trace = bmc.get_last_trace()
        self.assertIsInstance(trace, intrepyd.trace.Trace)
        self.assertEqual({target: ['F', 'T']}, trace.get_as_net_dictionary())
        self.assertIn(('PUT', 'engines/addtarget', None,
                       {'net': 't', 'engine': 'e0', 'context': ctx.name}), service.calls)

    def test_portfolio(self):
        service = FakeService({'engines/create': [(201, {'result': 'e0'})],
                               'engines/reachtargets': [(200, {'result': 'unreachable'})],
                               'engines/lastengine': [(200, {'result': 'pdr'})]})
        ctx = RemoteContext(transport=service)
        portfolio = ctx.mk_portfolio(engines=('bmc', 'pdr'), max_depth=5)
        self.assertEqual(EngineResult.UNREACHABLE, portfolio.reach_targets(timeout=10))
        self.assertEqual('pdr', portfolio.get_last_engine())
        self.assertEqual(('POST', 'engines/create', None,
                          {'engines': ['bmc', 'pdr'], 'max_depth': 5, 'engine': 'portfolio',
                           'context': ctx.name}), service.calls[1])
        self.assertEqual(('PUT', 'engines/reachtargets', None,
                          {'timeout': 10, 'engine': 'e0', 'context': ctx.name}),
                         service.calls[2])

    def test_error(self):
        service = FakeService({'nets/nots/create': [(400, {'result': "error: unknown 'x'"})]})
        ctx = RemoteContext(transport=service)
        with self.assertRaises(RemoteError) as raised:
            ctx.mk_not(Net('x'))
        self.assertEqual(400, raised.exception.status)
        self.assertEqual("error: unknown 'x'", raised.exception.message)


if __name__ == '__main__':
    unittest.main()
