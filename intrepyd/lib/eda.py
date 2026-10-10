"""
Implementation of EDA-specific components
"""

def mk_clock(ctx, name):
    """
    Creates a clock signal
    """
    bool_t = ctx.mk_boolean_type()
    i = ctx.mk_input(name + '_input', bool_t)
    first = ctx.mk_latch(name + '_first', bool_t)
    ctx.set_latch_init_next(first, ctx.mk_true(), ctx.mk_false())
    inv = ctx.mk_latch(name + '_inv', bool_t)
    clk = ctx.mk_ite(first, i, inv, name=name)
    ctx.set_latch_init_next(inv, ctx.mk_true(), ctx.mk_not(clk))
    return clk, i

def mk_counter(context, name, typ, limit, init=None, increment=None, enable=None, reset=None):
    """
    Counts from init to limit by increment. Returns the
    value of the counter and whether the limit has been
    reached or not. An enable signal and a reset signal
    may also be specified.

    Args:
        context: the context to use
        name: the unique name of this counter
        type: the type of the data stored in the counter
        limit: the limit after which the counter saturates
        init (=0): the initial value of the counter
        increment (=1): the increment value
        enable (=true): the counter is incremented only if enable is true
        reset (=false): resets the counter to the initial value

    Returns:
        counter: the current value of the counter
        Q: true iff the counter has reached saturation
    """
    if init is None:
        init = context.mk_number("0", typ)
    if increment is None:
        increment = context.mk_number("1", typ)
    if enable is None:
        enable = context.mk_true()
    if reset is None:
        reset = context.mk_false()

    counter = context.mk_latch(name, typ)
    not_q = context.mk_lt(counter, limit)
    nex = context.mk_ite(reset,\
                         init,\
                         context.mk_ite(context.mk_and(enable, not_q),\
                                        context.mk_add(counter, increment),\
                                        counter))
    context.set_latch_init_next(counter, init, nex)
    q = context.mk_not(not_q, name + '.Q')
    return counter, q

class LatchD:
    r"""
    LatchD (LD)

    A latch with enable

    Symbol:
          ____
         |    |
    D ---| LD |--- Q
         |    |
    E ---|    |
         |____|

    Diagram:
        A latch wrapped around a mux

        +--------------------+
        |   __               |
        |  |  \      ____    |
        +--| 0 |    |    |   |
           |   |----| L  |---+--- Q
      D ---| 1 |    |    |
           |__/     |____|
             |
             |
      E -----+
    """
    def __init__(self, ctx, name, t):
        """
        Args:
            ctx: the context to use
            name: the unique name
            t: the type of the data stored
        """
        self._ctx = ctx
        self._name = name
        self.q = ctx.mk_latch(name, t)

    def set_init_next(self, init, d, e):
        """
        Sets the initial value of the latch

        Args:
            init: the initial value
            D: the input signal
            E: the enable signal
        """
        ite = self._ctx.mk_ite(e, d, self.q)
        self._ctx.set_latch_init_next(self.q, init, ite)

class Delay:
    r"""
    Delay (D)

    Delays a signal by one full clock cycle

    Symbol:
          ____
         |    |
    D ---| D  |--- Q
         |    |
         |>   |
         |____|

    Diagram:
        Two latches in series

          ____     ____
         |    |   |    |
    D ---| L  |---| L  |--- Q
         |    |   |    |
         |____|   |____|
    """
    def __init__(self, ctx, name, t):
        """
        Args:
            ctx: the context to use
            name: the unique name
            t: the type of the data stored
        """
        self._ctx = ctx
        self._name = name
        self._l = ctx.mk_latch(name + '_back', t)
        self.q = ctx.mk_latch(name, t)

    def set_init_next(self, init, d):
        """
        Sets the initial value of the latch

        Args:
            init: the "fill" value for the first cycle
            D: the input signal
        """
        self._ctx.set_latch_init_next(self._l, init, d)
        self._ctx.set_latch_init_next(self.q, init, self._l)


class FlipFlopD:
    r"""
    Flip Flop D (FFD)

    Args:
        ctx: the context to use
        name: the unique name
        t: the type of the data stored
        C: the clock signal

    Returns:
        Q: the value stored in the flip flop

    Symbol:
          _____
         |     |
    D ---| FFD |--- Q
         |     |
    C ---|>    |
         |_____|

    Diagram:
        It consists of a master DL and a slave LD. The
        diagram shows the raising-edge version (notice
        the negated clock in the master latchD)

                        +---------------------+
                        |   ____              |
           _____        |  |    |             |
          |     |       +--| L  |---+   __    |
    D ----| LD  |---+      |    |   |  |  \   |
          |     |   |      |____|   +--| 0 |  |
    C -+-o|     |   |                  |   |--+-- Q
       |  |_____|   +------------------| 1 |
       |                               |__/
       |                                 |
       +---------------------------------+
    """
    def __init__(self, ctx, name, t, c):
        """
        Args:
            ctx: the context to use
            name: the unique name
            t: the type of the data stored
            C: the clock signal
        """
        self._ctx = ctx
        self._name = name
        self._master = LatchD(ctx, name + '_master', t)
        self._slave = ctx.mk_latch(name + '_slave', t)
        self.q = self._ctx.mk_ite(c, self._master.q, self._slave, name + '.Q')
        self._c = c

    def set_init_next(self, init, d):
        """
        Sets the initial and next value

        Args:
            init: the initial value
            D: the flip flop input signal
        """
        self._master.set_init_next(init, d, self._ctx.mk_not(self._c))
        self._ctx.set_latch_init_next(self._slave, init, self.q)

class FlipFlopDE:
    r"""
    Flip Flop D with Enable (FFDE)

    Symbol:
          _____
         |     |
    D ---| FFD |--- Q
    E ---|     |
    C ---|>    |
         |_____|

    Diagram:

    It consists of a FFD wrapped by a mux

       +--------------------+
       |   __               |
       |  |  \     _____    |
       +--| 0 |   |     |   |
          |   |---| FFD |---+--- Q
     D ---| 1 |   |     |
          |__/  +-|>    |
            |   | |_____|
     E -----+   |
                |
     C ---------+

    """
    def __init__(self, ctx, name, t, c):
        """
        Args:
            ctx: the context to use
            name: the unique name
            t: the type of the data stored
            C: the clock signal
        """
        self._ctx = ctx
        self._name = name
        self._master = LatchD(ctx, name + '_master', t)
        self._slave = ctx.mk_latch(name + '_slave', t)
        self.q = self._ctx.mk_ite(c, self._master.q, self._slave, name + '.Q')
        self._c = c

    def set_init_next(self, init, d, e):
        """
        Sets the initial and next value

        Args:
            init: the initial value
            D: the flip flop input signal
            E: the flip flop enable signal
        """
        mux = self._ctx.mk_ite(e, d, self.q)
        self._master.set_init_next(init, mux, self._ctx.mk_not(self._c))
        self._ctx.set_latch_init_next(self._slave, init, self.q)


def mk_mux(ctx, sel, in0, in1, name=None):
    """
    A 2:1 multiplexer: returns ``in1`` when ``sel`` is true, else ``in0``.

    Symbol::

           __
          |  \
          | 1 |--- Q     Q = in1 if sel else in0
    in1 --|   |
          | 0 |
    in0 --|__/
            |
    sel ----+

    Args:
        ctx: the context to use
        sel: the boolean selector net
        in0: the net selected when sel is false
        in1: the net selected when sel is true
        name: an optional name for the output net

    Returns:
        the output net
    """
    return ctx.mk_ite(sel, in1, in0, name=name)


class ShiftRegister:
    r"""
    Shift register (SR)

    A chain of ``length`` one-cycle registers: the output ``q`` is the input
    ``d`` delayed by ``length`` cycles. ``stages[i]`` is the output of the
    i-th register, so ``stages[0]`` is ``d`` delayed by one cycle and
    ``stages[-1]`` is ``q``.

    Diagram::

          ____     ____           ____
         |    |   |    |         |    |
    D ---| L0 |---| L1 |-- ... --|Ln-1|--- Q
         |____|   |____|         |____|
    """
    def __init__(self, ctx, name, t, length):
        """
        Args:
            ctx: the context to use
            name: the unique name
            t: the type of the data shifted
            length: the number of stages (must be >= 1)
        """
        if length < 1:
            raise ValueError('a shift register needs at least one stage')
        self._ctx = ctx
        self._name = name
        self.stages = [ctx.mk_latch(name + '_' + str(i), t) for i in range(length)]
        self.q = self.stages[-1]

    def set_init_next(self, init, d):
        """
        Closes the register chain.

        Args:
            init: the value every stage holds for its first cycles
            d: the input signal shifted into the first stage
        """
        previous = d
        for latch in self.stages:
            self._ctx.set_latch_init_next(latch, init, previous)
            previous = latch
