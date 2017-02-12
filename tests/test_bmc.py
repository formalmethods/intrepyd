import intrepyd as ip
from intrepyd.engine import EngineResult
import unittest

class TestBmc(unittest.TestCase):

    def test_bmc_01(self):
        context = ip.Context()
        bt = context.mk_boolean_type()
        x = context.mk_input("x", bt)
        y = context.mk_input("y", bt)
        gate = context.mk_and(x, y)
        context.mk_output(gate)
        bmc = context.mk_bmc()
        bmc.add_target(gate)
        bmc.set_current_depth(0)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.REACHABLE, result)

    def test_bmc_02(self):
        context = ip.Context()
        bt = context.mk_boolean_type()
        x = context.mk_input("x", bt)
        y = context.mk_input("y", bt)
        gate = context.mk_and(x, y)
        context.mk_output(gate)
        bmc = context.mk_bmc()
        bmc.add_target(gate)
        bmc.set_current_depth(0)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.REACHABLE, result)
        trace = bmc.get_last_trace()
        self.assertEquals(1, ip.trace.Trace.get_numeric_value(trace.get_value(x, 0)))
        self.assertEquals(1, ip.trace.Trace.get_numeric_value(trace.get_value(y, 0)))

    def test_bmc_03(self):
        context = ip.Context()
        bt = context.mk_boolean_type()
        x = context.mk_input("x", bt)
        y = context.mk_input("y", bt)
        gate = context.mk_and(context.mk_not(x), y)
        context.mk_output(gate)
        context.mk_assumption(x)
        bmc = context.mk_bmc()
        bmc.add_target(gate)
        bmc.set_current_depth(0)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.UNREACHABLE, result)

    def test_bmc_04(self):
        context = ip.Context()
        bt = context.mk_boolean_type()
        f = context.mk_false()
        t = context.mk_true()
        l1 = context.mk_latch('l1', bt)
        l2 = context.mk_latch('l2', bt)
        l3 = context.mk_latch('l3', bt)
        context.set_latch_init_next(l1, t, l3)
        context.set_latch_init_next(l2, f, l1)
        context.set_latch_init_next(l3, f, l2)
        bmc = context.mk_bmc()
        bmc.add_target(l3)
        bmc.add_watch(l1)
        bmc.add_watch(l2)
        bmc.add_watch(l3)
        bmc.set_current_depth(0)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.UNREACHABLE, result)
        bmc.set_current_depth(1)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.UNREACHABLE, result)
        bmc.set_current_depth(2)
        result = bmc.reach_targets()
        self.assertEquals(EngineResult.REACHABLE, result)
    
if __name__ == '__main__':
    unittest.main()
