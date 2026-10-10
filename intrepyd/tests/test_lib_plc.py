import unittest
import intrepyd as ip
from intrepyd.lib.plc import mk_r_trig, mk_f_trig, mk_sr, mk_rs, mk_ctu


def _simulate(ctx, inputs, watched, depth):
    """Drives `inputs` ({net: [values]}) and returns {net: [values]} of `watched`."""
    tr = ctx.mk_trace()
    for net, values in inputs.items():
        for t, value in enumerate(values):
            tr.set_value(net, t, value)
    simulator = ctx.mk_simulator()
    for net in watched:
        simulator.add_watch(net)
    simulator.simulate(tr, depth)
    return {net: [tr.get_value(net, t) for t in range(depth + 1)] for net in watched}


class TestPlc(unittest.TestCase):

    def test_r_trig_pulses_on_rising_edges(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        clk = ctx.mk_input('clk', bt)
        q = mk_r_trig(ctx, clk, 'rtrig')
        clk_vals = ['F', 'T', 'T', 'F', 'T']
        out = _simulate(ctx, {clk: clk_vals}, [q], len(clk_vals) - 1)
        # rising edges at t1 (F->T) and t4 (F->T); t2 stays T, no edge
        self.assertEqual(['F', 'T', 'F', 'F', 'T'], out[q])

    def test_f_trig_pulses_on_falling_edges(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        clk = ctx.mk_input('clk', bt)
        q = mk_f_trig(ctx, clk, 'ftrig')
        clk_vals = ['T', 'F', 'F', 'T', 'F']
        out = _simulate(ctx, {clk: clk_vals}, [q], len(clk_vals) - 1)
        # memory starts true, so no edge at t0; falling edges at t1 and t4
        self.assertEqual(['F', 'T', 'F', 'F', 'T'], out[q])

    def test_sr_is_set_dominant(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        s = ctx.mk_input('s', bt)
        r = ctx.mk_input('r', bt)
        q = mk_sr(ctx, s, r, 'sr')
        #        t0   t1   t2   t3   t4
        s_vals = ['T', 'F', 'F', 'T', 'F']
        r_vals = ['F', 'F', 'T', 'T', 'F']
        out = _simulate(ctx, {s: s_vals, r: r_vals}, [q], 5)
        # q starts false; q(t+1) = s(t) or (q(t) and not r(t))
        # q0=F, q1=T (set), q2=T (hold), q3=F (reset), q4=T (set dominates), q5=T
        self.assertEqual(['F', 'T', 'T', 'F', 'T', 'T'], out[q])

    def test_rs_is_reset_dominant(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        s = ctx.mk_input('s', bt)
        r = ctx.mk_input('r', bt)
        q = mk_rs(ctx, s, r, 'rs')
        s_vals = ['T', 'F', 'T', 'F']
        r_vals = ['F', 'F', 'T', 'F']
        out = _simulate(ctx, {s: s_vals, r: r_vals}, [q], 4)
        # q0=F, q1=T (set), q2=T (hold), q3=F (reset dominates set), q4=F
        self.assertEqual(['F', 'T', 'T', 'F', 'F'], out[q])

    def test_ctu_counts_rising_edges_up_to_pv(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        cu = ctx.mk_input('cu', bt)
        reset = ctx.mk_input('reset', bt)
        pv = ctx.mk_number('2', it)
        cv, q = mk_ctu(ctx, 'ctu', cu, reset, pv, it)
        #           t0   t1   t2   t3   t4   t5
        cu_vals =  ['F', 'T', 'F', 'T', 'F', 'T']  # rising edges at t1, t3, t5
        rst_vals = ['F', 'F', 'F', 'F', 'F', 'F']
        out = _simulate(ctx, {cu: cu_vals, reset: rst_vals}, [cv, q], 6)
        # count rises on each rising edge, saturating at pv=2
        self.assertEqual(['0', '0', '1', '1', '2', '2', '2'], out[cv])
        # Q is true once the count reaches pv
        self.assertEqual(['F', 'F', 'F', 'F', 'T', 'T', 'T'], out[q])

    def test_ctu_reset_forces_zero(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        cu = ctx.mk_input('cu', bt)
        reset = ctx.mk_input('reset', bt)
        pv = ctx.mk_number('2', it)
        cv, _ = mk_ctu(ctx, 'ctu', cu, reset, pv, it)
        cu_vals =  ['F', 'T', 'F', 'T', 'F']
        rst_vals = ['F', 'F', 'F', 'T', 'F']  # reset asserted at t3
        out = _simulate(ctx, {cu: cu_vals, reset: rst_vals}, [cv], 5)
        # counts to 1 at t2, 2 at t4 would be; reset at t3 zeroes the next cycle
        self.assertEqual('1', out[cv][2])
        self.assertEqual('0', out[cv][4])


if __name__ == '__main__':
    unittest.main()
