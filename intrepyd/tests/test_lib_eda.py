import intrepyd as ip
from intrepyd.lib.eda import mk_clock, mk_counter, LatchD, Delay, FlipFlopD, FlipFlopDE,\
                            mk_mux, ShiftRegister
from intrepyd.engine import EngineResult
import unittest

class TestComponents(unittest.TestCase):

    def test_counter(self):
        ctx = ip.Context()
        int8type = ctx.mk_int8_type()
        ten = ctx.mk_number("10", int8type)
        counter, q = mk_counter(ctx, "counter", typ=int8type, limit=ten)
        simulator = ctx.mk_simulator()
        trace = ctx.mk_trace()
        simulator.add_watch(counter)
        simulator.add_watch(q)
        simulator.simulate(trace, 12)
        self.assertEqual('9', trace.get_value(counter, 9))
        self.assertEqual('F', trace.get_value(q, 9))
        self.assertEqual('10', trace.get_value(counter, 10))
        self.assertEqual('T', trace.get_value(q, 10))
        self.assertEqual('10', trace.get_value(counter, 11))
        self.assertEqual('T', trace.get_value(q, 11))

    def test_latch_d_is_transparent_when_enabled(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        latchD = LatchD(ctx, 'l', bt)
        latchD.set_init_next(ctx.mk_true(), i, ctx.mk_true())
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'T')
        tr.set_value(i, 1, 'F')
        tr.set_value(i, 2, 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(latchD.q)
        simulator.simulate(tr, 3)
        self.assertEqual('T', tr.get_value(latchD.q, 0))
        self.assertEqual('T', tr.get_value(latchD.q, 1))
        self.assertEqual('F', tr.get_value(latchD.q, 2))
        self.assertEqual('T', tr.get_value(latchD.q, 3))

    def test_latch_d_holds_previous_value_when_disabled(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        e = ctx.mk_input('e', bt)
        latchD = LatchD(ctx, 'l', bt)
        latchD.set_init_next(ctx.mk_true(), i, e)
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'T')
        tr.set_value(i, 1, 'F')
        tr.set_value(i, 2, 'F')
        tr.set_value(e, 0, 'T')
        tr.set_value(e, 1, 'F')
        tr.set_value(e, 2, 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(latchD.q)
        simulator.simulate(tr, 3)
        self.assertEqual('T', tr.get_value(latchD.q, 0))
        self.assertEqual('T', tr.get_value(latchD.q, 1))
        self.assertEqual('T', tr.get_value(latchD.q, 2))
        self.assertEqual('F', tr.get_value(latchD.q, 3))

    def test_flip_flop_d_raising_edge_01(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        clk = ctx.mk_input('clk', bt)
        ffd = FlipFlopD(ctx, 'ffd', bt, clk)
        ffd.set_init_next(ctx.mk_true(), i)
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'F') # re
        tr.set_value(i, 1, 'T') # fe << ignored
        tr.set_value(i, 2, 'T') # re
        tr.set_value(i, 3, 'T') # fe << ignored
        tr.set_value(i, 4, 'F') # re
        tr.set_value(i, 5, 'F') # fe << ignored
        for t in range(6):
            tr.set_value(clk, t, 'F' if t % 2 == 0 else 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(ffd.q)
        simulator.simulate(tr, 6)
        self.assertEqual('T', tr.get_value(ffd.q, 0))
        self.assertEqual('F', tr.get_value(ffd.q, 1))
        self.assertEqual('F', tr.get_value(ffd.q, 2))
        self.assertEqual('T', tr.get_value(ffd.q, 3))
        self.assertEqual('T', tr.get_value(ffd.q, 4))
        self.assertEqual('F', tr.get_value(ffd.q, 5))
        self.assertEqual('F', tr.get_value(ffd.q, 6))

    def test_flip_flop_d_raising_edge_02(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        clk = ctx.mk_input('clk', bt)
        ffd = FlipFlopD(ctx, 'ffd', bt, clk)
        ffd.set_init_next(ctx.mk_true(), i)
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'F') # re
        tr.set_value(i, 1, 'F') # fe << ignored
        tr.set_value(i, 2, 'T') # re
        tr.set_value(i, 3, 'F') # fe << ignored
        tr.set_value(i, 4, 'F') # re
        tr.set_value(i, 5, 'T') # fe << ignored
        for t in range(6):
            tr.set_value(clk, t, 'F' if t % 2 == 0 else 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(ffd.q)
        simulator.simulate(tr, 6)
        self.assertEqual('T', tr.get_value(ffd.q, 0))
        self.assertEqual('F', tr.get_value(ffd.q, 1))
        self.assertEqual('F', tr.get_value(ffd.q, 2))
        self.assertEqual('T', tr.get_value(ffd.q, 3))
        self.assertEqual('T', tr.get_value(ffd.q, 4))
        self.assertEqual('F', tr.get_value(ffd.q, 5))
        self.assertEqual('F', tr.get_value(ffd.q, 6))

    def test_flip_flop_de_raising_edge_01(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        e = ctx.mk_input('e', bt)
        clk = ctx.mk_input('clk', bt)
        ffd = FlipFlopDE(ctx, 'ffd', bt, clk)
        ffd.set_init_next(ctx.mk_true(), i, e)
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'F') # re
        tr.set_value(i, 1, 'F') # fe << ignored
        tr.set_value(i, 2, 'T') # re << ignored by enable
        tr.set_value(i, 3, 'F') # fe << ignored
        tr.set_value(i, 4, 'T') # re
        tr.set_value(i, 5, 'T') # fe << ignored
        tr.set_value(e, 0, 'T')
        tr.set_value(e, 1, 'T')
        tr.set_value(e, 2, 'F') # re << effective
        tr.set_value(e, 3, 'F') # fe << not effective
        tr.set_value(e, 4, 'T')
        tr.set_value(e, 5, 'T')
        for t in range(6):
            tr.set_value(clk, t, 'F' if t % 2 == 0 else 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(ffd.q)
        simulator.simulate(tr, 6)
        self.assertEqual('T', tr.get_value(ffd.q, 0))
        self.assertEqual('F', tr.get_value(ffd.q, 1))
        self.assertEqual('F', tr.get_value(ffd.q, 2))
        self.assertEqual('F', tr.get_value(ffd.q, 3))
        self.assertEqual('F', tr.get_value(ffd.q, 4))
        self.assertEqual('T', tr.get_value(ffd.q, 5))
        self.assertEqual('T', tr.get_value(ffd.q, 6))

    def test_flip_flop_de_raising_edge_02(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        i = ctx.mk_input('i', bt)
        e = ctx.mk_input('e', bt)
        clk = ctx.mk_input('clk', bt)
        ffd = FlipFlopDE(ctx, 'ffd', bt, clk)
        ffd.set_init_next(ctx.mk_true(), i, e)
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'T') # re
        tr.set_value(i, 1, 'F') # fe << ignored
        tr.set_value(i, 2, 'F') # re << ignored by enable
        tr.set_value(e, 0, 'T')
        tr.set_value(e, 1, 'T')
        tr.set_value(e, 2, 'F')
        for t in range(4):
            tr.set_value(clk, t, 'F' if t % 2 == 0 else 'T')
        simulator = ctx.mk_simulator()
        simulator.add_watch(ffd.q)
        simulator.simulate(tr, 6)
        self.assertEqual('T', tr.get_value(ffd.q, 0))
        self.assertEqual('T', tr.get_value(ffd.q, 1))
        self.assertEqual('T', tr.get_value(ffd.q, 2))
        self.assertEqual('T', tr.get_value(ffd.q, 3))

    def test_clock_can_start_at_T(self):
        ctx = ip.Context()
        clk, _ = mk_clock(ctx, 'clk')
        bmc = ctx.mk_bmc()
        bmc.set_current_depth(0)
        bmc.add_target(clk)
        result = bmc.reach_targets()
        self.assertEqual(result, EngineResult.REACHABLE)

    def test_clock_can_start_at_F(self):
        ctx = ip.Context()
        clk, _ = mk_clock(ctx, 'clk')
        bmc = ctx.mk_bmc()
        bmc.set_current_depth(0)
        bmc.add_target(ctx.mk_not(clk))
        result = bmc.reach_targets()
        self.assertEqual(result, EngineResult.REACHABLE)

    def test_clock_goes_up_and_down_starts_up(self):
        ctx = ip.Context()
        clk, _ = mk_clock(ctx, 'clk')
        it = ctx.mk_int8_type()
        _, Q = mk_counter(ctx, 'counter', it, ctx.mk_number('4', it))
        br = ctx.mk_backward_reach()
        target = ctx.mk_and(Q, clk)
        br.add_target(target)
        br.add_watch(clk)
        result = br.reach_targets()
        self.assertEqual(result, EngineResult.REACHABLE)
        tr = br.get_last_trace()
        self.assertEqual('T', tr.get_value(clk, 0))
        self.assertEqual('F', tr.get_value(clk, 1))
        self.assertEqual('T', tr.get_value(clk, 2))
        self.assertEqual('F', tr.get_value(clk, 3))
        self.assertEqual('T', tr.get_value(clk, 4))

    def test_clock_goes_up_and_down_starts_down(self):
        ctx = ip.Context()
        clk, _ = mk_clock(ctx, 'clk')
        it = ctx.mk_int8_type()
        _, Q = mk_counter(ctx, 'counter', it, ctx.mk_number('4', it))
        br = ctx.mk_backward_reach()
        target = ctx.mk_and(Q, ctx.mk_not(clk))
        br.add_target(target)
        br.add_watch(clk)
        result = br.reach_targets()
        self.assertEqual(result, EngineResult.REACHABLE)
        tr = br.get_last_trace()
        self.assertEqual('F', tr.get_value(clk, 0))
        self.assertEqual('T', tr.get_value(clk, 1))
        self.assertEqual('F', tr.get_value(clk, 2))
        self.assertEqual('T', tr.get_value(clk, 3))
        self.assertEqual('F', tr.get_value(clk, 4))

    def test_delay(self):
        ctx = ip.Context()
        t = ctx.mk_boolean_type()
        delay = Delay(ctx, 'delay', t)
        delay.set_init_next(ctx.mk_false(), ctx.mk_true())
        bmc = ctx.mk_bmc()
        bmc.add_target(delay.q)
        bmc.set_current_depth(0)
        result = bmc.reach_targets()
        self.assertEqual(result, EngineResult.UNKNOWN)
        bmc.set_current_depth(1)
        result = bmc.reach_targets()
        self.assertEqual(result, EngineResult.UNKNOWN)
        bmc.set_current_depth(2)
        result = bmc.reach_targets()
        self.assertEqual(result, EngineResult.REACHABLE)

    def test_clock_simulation(self):
        ctx = ip.Context()
        clock, i = mk_clock(ctx, 'clock')
        simulator = ctx.mk_simulator()
        tr = ctx.mk_trace()
        tr.set_value(i, 0, 'F')
        simulator.add_watch(clock)
        simulator.add_watch(i)
        simulator.simulate(tr, 10)
        self.assertEqual('F', tr.get_value(i, 0))
        for j in range(11):
            self.assertEqual('F' if j % 2 == 0 else 'T', tr.get_value(clock, j))

    def test_mux_selects_in1_when_true_in0_when_false(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        sel = ctx.mk_input('sel', bt)
        in0 = ctx.mk_input('in0', bt)
        in1 = ctx.mk_input('in1', bt)
        out = mk_mux(ctx, sel, in0, in1, 'out')
        tr = ctx.mk_trace()
        # (sel, in0, in1) -> expected out
        rows = [('F', 'T', 'F'),   # sel false -> in0 = T
                ('T', 'T', 'F'),   # sel true  -> in1 = F
                ('F', 'F', 'T'),   # sel false -> in0 = F
                ('T', 'F', 'T')]   # sel true  -> in1 = T
        for t, (s, a, b) in enumerate(rows):
            tr.set_value(sel, t, s)
            tr.set_value(in0, t, a)
            tr.set_value(in1, t, b)
        simulator = ctx.mk_simulator()
        simulator.add_watch(out)
        simulator.simulate(tr, len(rows) - 1)
        expected = ['T', 'F', 'F', 'T']
        for t, exp in enumerate(expected):
            self.assertEqual(exp, tr.get_value(out, t))

    def test_shift_register_delays_by_its_length(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        d = ctx.mk_input('d', bt)
        sr = ShiftRegister(ctx, 'sr', bt, 3)
        sr.set_init_next(ctx.mk_false(), d)
        values = ['T', 'F', 'T', 'F', 'F', 'T']
        tr = ctx.mk_trace()
        for t, v in enumerate(values):
            tr.set_value(d, t, v)
        simulator = ctx.mk_simulator()
        simulator.add_watch(sr.q)
        simulator.simulate(tr, len(values) + 3)
        # q is d delayed by 3 cycles; the first 3 cycles hold the init (F)
        self.assertEqual('F', tr.get_value(sr.q, 0))
        self.assertEqual('F', tr.get_value(sr.q, 1))
        self.assertEqual('F', tr.get_value(sr.q, 2))
        for t in range(len(values)):
            self.assertEqual(values[t], tr.get_value(sr.q, t + 3))

if __name__ == '__main__':
    unittest.main()
