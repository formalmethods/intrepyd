import os
import unittest

import intrepyd as ip
from intrepyd.engine import EngineResult
from intrepyd.tools import translate_lustre
from . import from_fixture_path


class TestPdr(unittest.TestCase):

    def test_needs_invariant(self):
        # c >= 0 is an invariant that k-induction cannot find
        ctx = ip.Context()
        t = ctx.mk_int_type()
        c = ctx.mk_latch('c', t)
        ctx.set_latch_init_next(c, ctx.mk_number('0', t), ctx.mk_add(c, ctx.mk_number('1', t)))
        pdr = ctx.mk_pdr()
        pdr.add_target(ctx.mk_eq(c, ctx.mk_number('-1', t)))
        self.assertEqual(EngineResult.UNREACHABLE, pdr.reach_targets())

    def test_counterexample(self):
        ctx = ip.Context()
        t = ctx.mk_int8_type()
        c = ctx.mk_latch('c', t)
        ctx.set_latch_init_next(c, ctx.mk_number('0', t), ctx.mk_add(c, ctx.mk_number('1', t)))
        pdr = ctx.mk_pdr()
        pdr.add_target(ctx.mk_eq(c, ctx.mk_number('5', t)))
        pdr.add_watch(c)
        self.assertEqual(EngineResult.REACHABLE, pdr.reach_targets())
        trace = pdr.get_last_trace()
        self.assertEqual(5, trace.get_max_depth())
        self.assertEqual('5', trace.get_value(c, 5))

    def test_lustre(self):
        try:
            enc = translate_lustre(from_fixture_path('lustre/peterson_1.lus'), 'top', 'real',
                                   'encoding_pdr', inttype='int')
        finally:
            if os.path.exists('encoding_pdr.py'):
                os.remove('encoding_pdr.py')
        ctx = ip.Context()
        circ = enc.mk_instance(ctx, 'peterson')
        circ.mk_circuit()
        pdr = ctx.mk_pdr()
        pdr.add_target(ctx.mk_not(circ.outputs['OK']))
        self.assertEqual(EngineResult.UNREACHABLE, pdr.reach_targets())


if __name__ == '__main__':
    unittest.main()
