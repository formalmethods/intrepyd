import os
import time
import unittest

import intrepyd as ip
from intrepyd import api
from intrepyd.engine import EngineResult
from intrepyd.recipe import replay
from intrepyd.tools import translate_lustre
from . import from_fixture_path


def mk_counter(ctx, limit):
    # c counts up to limit while the input x holds
    t = ctx.mk_int8_type()
    x = ctx.mk_input('x', ctx.mk_boolean_type())
    c = ctx.mk_latch('c', t)
    step = ctx.mk_and(x, ctx.mk_lt(c, ctx.mk_number(str(limit), t)))
    ctx.set_latch_init_next(c, ctx.mk_number('0', t),
                            ctx.mk_ite(step, ctx.mk_add(c, ctx.mk_number('1', t)), c))
    return c, t


class TestRecipe(unittest.TestCase):

    def test_replay(self):
        ctx = ip.Context()
        ctx.push_namespace('top')
        c, t = mk_counter(ctx, 5)
        target = ctx.mk_eq(c, ctx.mk_number('5', t), name='target')
        ctx.mk_output(target, name='out')
        ctx.pop_namespace()
        ctx.push_assumption(ctx.mk_true())
        copy = ip.Context()
        resolve = replay(ctx.recipe.calls, copy)
        self.assertEqual(sorted(ctx.nets), sorted(copy.nets))
        self.assertEqual(sorted(ctx.inputs), sorted(copy.inputs))
        self.assertEqual(sorted(ctx.latches), sorted(copy.latches))
        self.assertEqual(sorted(ctx.outputs), sorted(copy.outputs))
        self.assertEqual(copy.nets['top.target'], resolve(ctx.recipe.ref(target)))
        self.assertEqual(copy.latches['c'], resolve(ctx.recipe.ref(c)))

    def test_net_not_built_through_the_context(self):
        ctx = ip.Context()
        x = ctx.mk_input('x', ctx.mk_boolean_type())
        foreign = api.mk_not(ctx.ctx, x)
        with self.assertRaises(ValueError):
            ctx.recipe.ref(foreign)
        ctx.recipe.check()
        ctx.mk_and(x, foreign)
        with self.assertRaises(ValueError):
            ctx.recipe.check()


class TestPortfolio(unittest.TestCase):

    def test_counterexample(self):
        ctx = ip.Context()
        c, t = mk_counter(ctx, 5)
        portfolio = ctx.mk_portfolio()
        target = ctx.mk_eq(c, ctx.mk_number('5', t))
        portfolio.add_target(target)
        portfolio.add_watch(c)
        self.assertEqual(EngineResult.REACHABLE, portfolio.reach_targets(timeout=60))
        self.assertIn(portfolio.get_last_engine(), ('bmc', 'kind', 'br', 'pdr'))
        self.assertEqual((target,), portfolio.get_last_reached_targets())
        # The trace belongs to the caller's context
        trace = portfolio.get_last_trace()
        self.assertEqual(5, trace.get_max_depth())
        self.assertEqual(['0', '1', '2', '3', '4', '5'],
                         trace.get_as_net_dictionary()[c])

    def test_proof(self):
        ctx = ip.Context()
        c, t = mk_counter(ctx, 5)
        portfolio = ctx.mk_portfolio()
        portfolio.add_target(ctx.mk_gt(c, ctx.mk_number('5', t)))
        self.assertEqual(EngineResult.UNREACHABLE, portfolio.reach_targets(timeout=60))
        self.assertIn(portfolio.get_last_engine(), ('kind', 'br', 'pdr'))
        self.assertEqual((), portfolio.get_last_reached_targets())
        with self.assertRaises(Exception):
            portfolio.get_last_trace()

    def test_only_some_engines(self):
        # c >= 0 is an invariant that k-induction cannot find, but PDR can
        ctx = ip.Context()
        t = ctx.mk_int_type()
        c = ctx.mk_latch('c', t)
        ctx.set_latch_init_next(c, ctx.mk_number('0', t), ctx.mk_add(c, ctx.mk_number('1', t)))
        target = ctx.mk_eq(c, ctx.mk_number('-1', t))
        portfolio = ctx.mk_portfolio(engines=('pdr',))
        portfolio.add_target(target)
        self.assertEqual(EngineResult.UNREACHABLE, portfolio.reach_targets(timeout=60))
        self.assertEqual('pdr', portfolio.get_last_engine())
        # BMC alone cannot prove it: it gives up at max_depth
        portfolio = ctx.mk_portfolio(engines=('bmc',), max_depth=3)
        portfolio.add_target(target)
        self.assertFalse(portfolio.can_prove())
        self.assertEqual(EngineResult.UNKNOWN, portfolio.reach_targets(timeout=60))
        self.assertIsNone(portfolio.get_last_engine())

    def test_several_targets(self):
        ctx = ip.Context()
        c, t = mk_counter(ctx, 5)
        reachable = ctx.mk_eq(c, ctx.mk_number('3', t))
        unreachable = ctx.mk_eq(c, ctx.mk_number('6', t))
        portfolio = ctx.mk_portfolio()
        portfolio.add_target(unreachable)
        portfolio.add_target(reachable)
        self.assertEqual(EngineResult.REACHABLE, portfolio.reach_targets(timeout=60))
        self.assertEqual((reachable,), portfolio.get_last_reached_targets())
        portfolio.remove_last_reached_targets()
        self.assertEqual(EngineResult.UNREACHABLE, portfolio.reach_targets(timeout=60))

    def test_timeout(self):
        # A nonlinear target over unbounded integers, out of reach of every engine
        ctx = ip.Context()
        t = ctx.mk_int_type()
        x = ctx.mk_latch('x', t)
        y = ctx.mk_latch('y', t)
        a = ctx.mk_input('a', t)
        ctx.set_latch_init_next(x, ctx.mk_number('1', t), ctx.mk_add(x, a))
        ctx.set_latch_init_next(y, ctx.mk_number('1', t), ctx.mk_mul(y, x))
        cube = ctx.mk_mul(x, ctx.mk_mul(x, x))
        portfolio = ctx.mk_portfolio()
        portfolio.add_target(ctx.mk_eq(cube, ctx.mk_add(ctx.mk_mul(y, y),
                                                        ctx.mk_number('1000003', t))))
        start = time.monotonic()
        self.assertEqual(EngineResult.UNKNOWN, portfolio.reach_targets(timeout=2))
        self.assertLess(time.monotonic() - start, 30)
        self.assertIsNone(portfolio.get_last_engine())

    def test_errors(self):
        ctx = ip.Context()
        with self.assertRaises(ValueError):
            ctx.mk_portfolio(engines=('bmc', 'nonsense'))
        with self.assertRaises(ValueError):
            ctx.mk_portfolio(engines=())
        portfolio = ctx.mk_portfolio()
        with self.assertRaises(ValueError):
            portfolio.reach_targets()
        x = ctx.mk_input('x', ctx.mk_boolean_type())
        with self.assertRaises(ValueError):
            portfolio.add_target(api.mk_not(ctx.ctx, x))

    def test_lustre(self):
        try:
            enc = translate_lustre(from_fixture_path('lustre/peterson_1.lus'), 'top', 'real',
                                   'encoding_portfolio', inttype='int')
        finally:
            if os.path.exists('encoding_portfolio.py'):
                os.remove('encoding_portfolio.py')
        ctx = ip.Context()
        circ = enc.mk_instance(ctx, 'peterson')
        circ.mk_circuit()
        portfolio = ctx.mk_portfolio()
        portfolio.add_target(ctx.mk_not(circ.outputs['OK']))
        self.assertEqual(EngineResult.UNREACHABLE, portfolio.reach_targets(timeout=60))


if __name__ == '__main__':
    unittest.main()
