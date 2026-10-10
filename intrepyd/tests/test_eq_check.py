import unittest
from intrepyd.lib.eda import mk_clock, Delay, FlipFlopD, FlipFlopDE
from intrepyd.engine import EngineResult
from intrepyd.context import Context

class TestEqCheck(unittest.TestCase):

    def stc_helper(self, ctx, t):
        """
        These two designs are equivalent
                _____                      _____
               |     |                    |     |
        D -----| FFD |--------------------| FFD |--- Q1
        E -----|     |                    |     |
        C -+---|>    |                  +-|>    |
           |   |_____|                  | |_____|
           |                            |
           +----------------------------+
                _____                      _____
               |     |                    |     |
        D -----| FFD |--------------------| FFD |--- Q2
        E ---+-|     |                +---|     |
        C -+-|-|>    |                | +-|>    |
           | | |_____|     _____      | | |_____|
           | |            |     |     | |
           | +------------| D   |-----+ |
           |              |     |       |
           |              |>    |       |
           |              |_____|       |
           |                            |
           +----------------------------+
        """
        init = None
        if t == ctx.mk_boolean_type():
            init = ctx.mk_true()
        else:
            init = ctx.mk_number('0', t)
        # Common inputs
        d = ctx.mk_input('d', t)
        e = ctx.mk_input('e', ctx.mk_boolean_type())
        clk, _ = mk_clock(ctx, 'clk')
        # Design 1
        back_ffde_1 = FlipFlopDE(ctx, 'back1', t, clk)
        back_ffde_1.set_init_next(init, d, e)
        forth_ffd_1 = FlipFlopD(ctx, 'forth1', t, clk)
        forth_ffd_1.set_init_next(init, back_ffde_1.q)
        # Design 2
        back_ffde_2 = FlipFlopDE(ctx, 'back2', t, clk)
        back_ffde_2.set_init_next(init, d, e)
        e_prime = Delay(ctx, 'delay', ctx.mk_boolean_type())
        e_prime.set_init_next(ctx.mk_true(), e)
        forth_ffde_2 = FlipFlopDE(ctx, 'forth2', t, clk)
        forth_ffde_2.set_init_next(init, back_ffde_2.q, e_prime.q)
        # EQ check problem
        diff = None
        if t == ctx.mk_boolean_type():
            diff = ctx.mk_xor(forth_ffd_1.q, forth_ffde_2.q)
        else:
            diff = ctx.mk_neq(forth_ffd_1.q, forth_ffde_2.q)
        br = ctx.mk_backward_reach()
        br.add_target(diff)
        result = br.reach_targets()
        self.assertEqual(EngineResult.UNREACHABLE, result)

    def odc_helper(self, ctx, t):
        r"""
        These two designs are equivalent
                       _____
                      |     |
        I ------------| D   |----+
                      |     |    |
                      |>    |    |
                      |_____|    |
                                __
                _____          |  \        _____
               |     |    J ---| 0 |      |     |
        D -----| FFD |--+      |   |------| FFD |--- Q1
               |     |  +------| 1 |      |     |
        C -+---|>    |         |__/     +-|>    |
           |   |_____|                  | |_____|
           |                            |
           +----------------------------+
                       _____
                      |     |
        I --+---------| D   |----+
            |         |     |    |
            |         |>    |    |
            |         |_____|    |
            |                   __
            |   _____          |  \        _____
            |  |     |    J ---| 0 |      |     |
        D --|--| FFD |--+      |   |------| FFD |--- Q2
            +--|     |  +------| 1 |      |     |
        C -+---|>    |         |__/     +-|>    |
           |   |_____|                  | |_____|
           |                            |
           +----------------------------+
        """
        init = None
        if t == ctx.mk_boolean_type():
            init = ctx.mk_true()
        else:
            init = ctx.mk_number('0', t)
        # Common part
        d = ctx.mk_input('d', t)
        j = ctx.mk_input('j', t)
        i = ctx.mk_input('i', ctx.mk_boolean_type())
        clk, _ = mk_clock(ctx, 'clk')
        i_prime = Delay(ctx, 'delay', ctx.mk_boolean_type())
        i_prime.set_init_next(ctx.mk_false(), i)
        # Design 1
        back_ffd_1 = FlipFlopD(ctx, 'back1', t, clk)
        back_ffd_1.set_init_next(init, d)
        mux1 = ctx.mk_ite(i_prime.q, back_ffd_1.q, j, 'mux1')
        forth_ffd_1 = FlipFlopD(ctx, 'forth1', t, clk)
        forth_ffd_1.set_init_next(init, mux1)
        # Design 2
        back_ffde_2 = FlipFlopDE(ctx, 'back2', t, clk)
        back_ffde_2.set_init_next(init, d, i)
        mux2 = ctx.mk_ite(i_prime.q, back_ffde_2.q, j, 'mux2')
        forth_ffd_2 = FlipFlopD(ctx, 'forth2', t, clk)
        forth_ffd_2.set_init_next(init, mux2)
        # EQ check problem
        diff = None
        if t == ctx.mk_boolean_type():
            diff = ctx.mk_xor(forth_ffd_1.q, forth_ffd_2.q, 'diff')
        else:
            diff = ctx.mk_neq(forth_ffd_1.q, forth_ffd_2.q, 'diff')
        br = ctx.mk_backward_reach()
        br.add_target(diff)
        result = br.reach_targets()
        self.assertEqual(EngineResult.UNREACHABLE, result)

    def test_stc_bool(self):
        ctx = Context()
        self.stc_helper(ctx, ctx.mk_boolean_type())

    def test_stc_int8(self):
        ctx = Context()
        self.stc_helper(ctx, ctx.mk_int8_type())

    def test_odc_bool(self):
        ctx = Context()
        self.odc_helper(ctx, ctx.mk_boolean_type())

    def test_odc_int8(self):
        ctx = Context()
        self.odc_helper(ctx, ctx.mk_int8_type())

    def test_simple_eq(self):
        ctx = Context()
        t = ctx.mk_int8_type()
        init = ctx.mk_number('0', t)
        # Common inputs
        d = ctx.mk_input('d', t)
        e = ctx.mk_input('e', ctx.mk_boolean_type())
        clk, _ = mk_clock(ctx, 'clk')
        # Design 1
        back_ffde_1 = FlipFlopDE(ctx, 'back1', t, clk)
        back_ffde_1.set_init_next(init, d, e)
        # Design 2
        back_ffde_2 = FlipFlopDE(ctx, 'back2', t, clk)
        back_ffde_2.set_init_next(init, d, e)
        # EQ check problem
        diff = ctx.mk_neq(back_ffde_1.q, back_ffde_2.q)
        br = ctx.mk_backward_reach()
        br.add_target(diff)
        result = br.reach_targets()
        self.assertEqual(EngineResult.UNREACHABLE, result)

if __name__ == '__main__':
    unittest.main()