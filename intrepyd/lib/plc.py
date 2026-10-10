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


def mk_ton(ctx, name, in_, pt, typ):
    """
    On-delay timer (TON). ``Q`` becomes true once ``in_`` has been true for
    ``pt`` consecutive cycles, and stays true while ``in_`` stays true;
    ``in_`` going false resets the elapsed time and ``Q``.

    Args:
        ctx: the context to use
        name: the unique name (``ET`` is ``name``, ``Q`` is ``name.Q``)
        in_: the boolean input
        pt: the preset time, in cycles, as a net of type ``typ``
        typ: the type counting the elapsed time

    Returns:
        a pair ``(ET, Q)``: the elapsed-time net and the boolean output
    """
    zero = ctx.mk_number("0", typ)
    one = ctx.mk_number("1", typ)
    et = ctx.mk_latch(name, typ)
    below = ctx.mk_lt(et, pt)
    incremented = ctx.mk_add(et, one)
    # not in_ -> reset to 0; still ramping -> +1; otherwise hold at pt
    nxt = ctx.mk_ite(ctx.mk_not(in_), zero, ctx.mk_ite(below, incremented, et))
    ctx.set_latch_init_next(et, zero, nxt)
    q = ctx.mk_and(in_, ctx.mk_geq(et, pt), name=name + '.Q')
    return et, q


def mk_tof(ctx, name, in_, pt, typ):
    """
    Off-delay timer (TOF). ``Q`` follows ``in_`` up, and when ``in_`` goes
    false ``Q`` stays true for ``pt`` more cycles before dropping. ``Q`` starts
    false.

    Args:
        ctx: the context to use
        name: the unique name (``ET`` is ``name``, ``Q`` is ``name.Q``)
        in_: the boolean input
        pt: the preset time, in cycles, as a net of type ``typ``
        typ: the type counting the elapsed time

    Returns:
        a pair ``(ET, Q)``: the elapsed-time net and the boolean output
    """
    one = ctx.mk_number("1", typ)
    zero = ctx.mk_number("0", typ)
    et = ctx.mk_latch(name, typ)
    below = ctx.mk_lt(et, pt)
    incremented = ctx.mk_add(et, one)
    # in_ -> elapsed back to 0; else count up, saturating at pt
    nxt = ctx.mk_ite(in_, zero, ctx.mk_ite(below, incremented, et))
    # starts "expired" (et = pt), so Q is false until in_ is first seen
    ctx.set_latch_init_next(et, pt, nxt)
    q = ctx.mk_or(in_, ctx.mk_lt(et, pt), name=name + '.Q')
    return et, q


def mk_tp(ctx, name, in_, pt, typ):
    """
    Pulse timer (TP). A rising edge of ``in_`` makes ``Q`` true for exactly
    ``pt`` cycles; the pulse is not retriggerable (edges during the pulse are
    ignored).

    Args:
        ctx: the context to use
        name: the unique name (``ET`` is ``name``, ``Q`` is ``name.Q``)
        in_: the boolean input
        pt: the pulse width, in cycles, as a net of type ``typ``
        typ: the type counting the elapsed time

    Returns:
        a pair ``(ET, Q)``: the elapsed-time net and the boolean output
    """
    one = ctx.mk_number("1", typ)
    et = ctx.mk_latch(name, typ)
    edge = mk_r_trig(ctx, in_, name + '_edge')
    idle = ctx.mk_geq(et, pt)
    start = ctx.mk_and(edge, idle)
    below = ctx.mk_lt(et, pt)
    incremented = ctx.mk_add(et, one)
    # start -> elapsed 1 (this cycle counts as the pulse's first); running -> +1;
    # idle -> stay at pt
    nxt = ctx.mk_ite(start, one, ctx.mk_ite(below, incremented, et))
    ctx.set_latch_init_next(et, pt, nxt)
    q = ctx.mk_or(below, start, name=name + '.Q')
    return et, q


def mk_ctd(ctx, name, cd, load, pv, typ):
    """
    Down counter (CTD). ``load`` sets the count ``CV`` to the preset ``pv``;
    each rising edge of ``cd`` lowers ``CV`` by one, down to zero. ``Q`` is true
    while ``CV <= 0``. ``CV`` starts at zero (so ``Q`` starts true until loaded).

    Args:
        ctx: the context to use
        name: the unique name (``CV`` is ``name``, ``Q`` is ``name.Q``)
        cd: the count-down signal (counted on its rising edge)
        load: loads ``pv`` into ``CV`` when true
        pv: the preset value net (of type ``typ``)
        typ: the type of the count

    Returns:
        a pair ``(CV, Q)``: the current count net and the boolean ``CV <= 0``
    """
    zero = ctx.mk_number("0", typ)
    one = ctx.mk_number("1", typ)
    cd_edge = mk_r_trig(ctx, cd, name + '_cd')
    cv = ctx.mk_latch(name, typ)
    above = ctx.mk_gt(cv, zero)
    decremented = ctx.mk_sub(cv, one)
    counting = ctx.mk_and(cd_edge, above)
    nxt = ctx.mk_ite(load, pv, ctx.mk_ite(counting, decremented, cv))
    ctx.set_latch_init_next(cv, zero, nxt)
    q = ctx.mk_leq(cv, zero, name=name + '.Q')
    return cv, q


def mk_ctud(ctx, name, cu, cd, reset, load, pv, typ):
    """
    Up-down counter (CTUD). A rising edge of ``cu`` raises the count ``CV``, a
    rising edge of ``cd`` lowers it (down to zero); ``reset`` forces it to zero
    and ``load`` sets it to the preset ``pv``, with priority reset > load > up >
    down. ``QU`` is ``CV >= pv`` and ``QD`` is ``CV <= 0``. ``CV`` starts at
    zero.

    Args:
        ctx: the context to use
        name: the unique name (``CV`` is ``name``, ``QU``/``QD`` are
            ``name.QU``/``name.QD``)
        cu: the count-up signal (counted on its rising edge)
        cd: the count-down signal (counted on its rising edge)
        reset: forces ``CV`` to zero when true
        load: loads ``pv`` into ``CV`` when true
        pv: the preset value net (of type ``typ``)
        typ: the type of the count

    Returns:
        a triple ``(CV, QU, QD)``
    """
    zero = ctx.mk_number("0", typ)
    one = ctx.mk_number("1", typ)
    cu_edge = mk_r_trig(ctx, cu, name + '_cu')
    cd_edge = mk_r_trig(ctx, cd, name + '_cd')
    cv = ctx.mk_latch(name, typ)
    up = ctx.mk_and(cu_edge, ctx.mk_not(cd_edge))
    down = ctx.mk_and(cd_edge, ctx.mk_not(cu_edge))
    above = ctx.mk_gt(cv, zero)
    incremented = ctx.mk_add(cv, one)
    decremented = ctx.mk_sub(cv, one)
    nxt = ctx.mk_ite(reset, zero,
                     ctx.mk_ite(load, pv,
                                ctx.mk_ite(up, incremented,
                                           ctx.mk_ite(ctx.mk_and(down, above), decremented, cv))))
    ctx.set_latch_init_next(cv, zero, nxt)
    qu = ctx.mk_geq(cv, pv, name=name + '.QU')
    qd = ctx.mk_leq(cv, zero, name=name + '.QD')
    return cv, qu, qd
