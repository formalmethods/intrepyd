"""
The standard function blocks of IEC 61131-3, the PLC programming standard, as
reusable intrepyd components.

Everything here is modelled on a **synchronous cycle**: one simulation step is
one PLC scan cycle. The edge detectors are combinational in the current and the
previous cycle (so a detected edge appears in the same cycle), while the
bistables and the counter hold their output in a latch, so it updates on the
next cycle — the usual way these blocks enter a cycle-based model checker.
"""


def mk_r_trig(ctx, clk, name):
    """
    Rising-edge detector (R_TRIG). ``Q`` is true for the one cycle in which
    ``clk`` goes from false to true. Following IEC 61131-3, the internal memory
    starts false, so an initial ``clk`` already true counts as a rising edge.

    ``Q := clk AND NOT M;  M := clk;  M(0) = false``

    Args:
        ctx: the context to use
        clk: the boolean signal to watch
        name: the unique name (the output net is named ``name``)

    Returns:
        the boolean edge net ``Q``
    """
    bt = ctx.mk_boolean_type()
    mem = ctx.mk_latch(name + '_mem', bt)
    ctx.set_latch_init_next(mem, ctx.mk_false(), clk)
    return ctx.mk_and(clk, ctx.mk_not(mem), name=name)


def mk_f_trig(ctx, clk, name):
    """
    Falling-edge detector (F_TRIG). ``Q`` is true for the one cycle in which
    ``clk`` goes from true to false. Following IEC 61131-3, the internal memory
    starts true, so no edge is reported in the first cycle.

    ``Q := NOT clk AND M;  M := clk;  M(0) = true``

    Args:
        ctx: the context to use
        clk: the boolean signal to watch
        name: the unique name (the output net is named ``name``)

    Returns:
        the boolean edge net ``Q``
    """
    bt = ctx.mk_boolean_type()
    mem = ctx.mk_latch(name + '_mem', bt)
    ctx.set_latch_init_next(mem, ctx.mk_true(), clk)
    return ctx.mk_and(ctx.mk_not(clk), mem, name=name)


def mk_sr(ctx, s, r, name):
    """
    Set-dominant bistable (SR). The output is held in a latch, starting false;
    when both ``s`` and ``r`` are true, the set wins.

    ``Q(0) = false;  Q := s OR (Q AND NOT r)``

    Args:
        ctx: the context to use
        s: the set signal
        r: the reset signal
        name: the unique name (the output latch is named ``name``)

    Returns:
        the boolean output net ``Q``
    """
    bt = ctx.mk_boolean_type()
    q = ctx.mk_latch(name, bt)
    nxt = ctx.mk_or(s, ctx.mk_and(q, ctx.mk_not(r)))
    ctx.set_latch_init_next(q, ctx.mk_false(), nxt)
    return q


def mk_rs(ctx, s, r, name):
    """
    Reset-dominant bistable (RS). The output is held in a latch, starting
    false; when both ``s`` and ``r`` are true, the reset wins.

    ``Q(0) = false;  Q := NOT r AND (s OR Q)``

    Args:
        ctx: the context to use
        s: the set signal
        r: the reset signal
        name: the unique name (the output latch is named ``name``)

    Returns:
        the boolean output net ``Q``
    """
    bt = ctx.mk_boolean_type()
    q = ctx.mk_latch(name, bt)
    nxt = ctx.mk_and(ctx.mk_not(r), ctx.mk_or(s, q))
    ctx.set_latch_init_next(q, ctx.mk_false(), nxt)
    return q


def mk_ctu(ctx, name, cu, reset, pv, typ):
    """
    Up counter (CTU). On each rising edge of ``cu`` the count ``CV`` goes up by
    one, saturating at the preset ``pv``; ``reset`` forces ``CV`` back to zero.
    ``Q`` is true while ``CV >= pv``. ``CV`` starts at zero.

    Args:
        ctx: the context to use
        name: the unique name (``CV`` is named ``name``, ``Q`` ``name.Q``)
        cu: the count-up signal (counted on its rising edge)
        reset: resets the count to zero when true
        pv: the preset value net (of type ``typ``)
        typ: the type of the count

    Returns:
        a pair ``(CV, Q)``: the current count net and the boolean ``CV >= pv``
    """
    zero = ctx.mk_number("0", typ)
    one = ctx.mk_number("1", typ)
    cu_edge = mk_r_trig(ctx, cu, name + '_cu')
    cv = ctx.mk_latch(name, typ)
    below_pv = ctx.mk_lt(cv, pv)
    incremented = ctx.mk_add(cv, one)
    counting = ctx.mk_and(cu_edge, below_pv)
    nxt = ctx.mk_ite(reset, zero, ctx.mk_ite(counting, incremented, cv))
    ctx.set_latch_init_next(cv, zero, nxt)
    q = ctx.mk_geq(cv, pv, name + '.Q')
    return cv, q
