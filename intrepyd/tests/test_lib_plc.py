import unittest
import intrepyd as ip
from intrepyd.lib.plc import (mk_r_trig, mk_f_trig, mk_sr, mk_rs, mk_ctu,
                              mk_ton, mk_tof, mk_tp, mk_ctd, mk_ctud)


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

    def test_ton_turns_on_after_pt_cycles(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        in_ = ctx.mk_input('in', bt)
        _, q = mk_ton(ctx, 'ton', in_, ctx.mk_number('3', it), it)
        in_vals = ['F', 'T', 'T', 'T', 'T', 'F', 'T', 'F']
        out = _simulate(ctx, {in_: in_vals}, [q], 7)
        # in true from t1; Q true once it has been true for 3 cycles (t4), and
        # drops as soon as in drops (t5)
        self.assertEqual(['F', 'F', 'F', 'F', 'T', 'F', 'F', 'F'], out[q])

    def test_tof_stays_on_for_pt_cycles_after_input_drops(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        in_ = ctx.mk_input('in', bt)
        _, q = mk_tof(ctx, 'tof', in_, ctx.mk_number('2', it), it)
        in_vals = ['F', 'T', 'T', 'F', 'F', 'F', 'T', 'F']
        out = _simulate(ctx, {in_: in_vals}, [q], 7)
        # Q follows in up (t1,t2); in drops at t3, Q holds 2 more cycles (t3,t4)
        # then drops at t5; rises again with in at t6 and holds at t7
        self.assertEqual(['F', 'T', 'T', 'T', 'T', 'F', 'T', 'T'], out[q])

    def test_tp_pulses_for_exactly_pt_cycles_not_retriggerable(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        in_ = ctx.mk_input('in', bt)
        _, q = mk_tp(ctx, 'tp', in_, ctx.mk_number('3', it), it)
        in_vals = ['F', 'T', 'F', 'F', 'F', 'T', 'T', 'F']
        out = _simulate(ctx, {in_: in_vals}, [q], 7)
        # rising edge at t1 -> pulse t1..t3 (3 cycles); next edge at t5 -> t5..t7
        self.assertEqual(['F', 'T', 'T', 'T', 'F', 'T', 'T', 'T'], out[q])

    def test_ctd_counts_down_from_loaded_value(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        cd = ctx.mk_input('cd', bt)
        load = ctx.mk_input('load', bt)
        cv, q = mk_ctd(ctx, 'ctd', cd, load, ctx.mk_number('2', it), it)
        cd_vals =   ['F', 'F', 'T', 'F', 'T', 'F', 'T', 'F']
        load_vals = ['T', 'F', 'F', 'F', 'F', 'F', 'F', 'F']
        out = _simulate(ctx, {cd: cd_vals, load: load_vals}, [cv, q], 7)
        # load 2 at t0; each cd rising edge lowers cv, flooring at 0
        self.assertEqual(['0', '2', '2', '1', '1', '0', '0', '0'], out[cv])
        self.assertEqual(['T', 'F', 'F', 'F', 'F', 'T', 'T', 'T'], out[q])

    def test_ctud_counts_up_and_down(self):
        ctx = ip.Context()
        bt = ctx.mk_boolean_type()
        it = ctx.mk_int8_type()
        cu = ctx.mk_input('cu', bt)
        cd = ctx.mk_input('cd', bt)
        reset = ctx.mk_input('r', bt)
        load = ctx.mk_input('l', bt)
        cv, qu, qd = mk_ctud(ctx, 'ctud', cu, cd, reset, load, ctx.mk_number('2', it), it)
        cu_vals = ['F', 'T', 'F', 'T', 'F', 'F', 'F', 'F']
        cd_vals = ['F', 'F', 'F', 'F', 'F', 'T', 'F', 'T']
        off =     ['F', 'F', 'F', 'F', 'F', 'F', 'F', 'F']
        out = _simulate(ctx, {cu: cu_vals, cd: cd_vals, reset: off, load: off}, [cv, qu, qd], 7)
        # up on cu edges (t1,t3) to 2, down on cd edges (t5,t7)
        self.assertEqual(['0', '0', '1', '1', '2', '2', '1', '1'], out[cv])
        self.assertEqual(['F', 'F', 'F', 'F', 'T', 'T', 'F', 'F'], out[qu])
        self.assertEqual(['T', 'T', 'F', 'F', 'F', 'F', 'F', 'F'], out[qd])


if __name__ == '__main__':
    unittest.main()
