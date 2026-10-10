"""
A structured library of reusable intrepyd components.

Two submodules:

- :mod:`intrepyd.lib.eda`: hardware/EDA blocks — a clock, a counter, latches,
  flip-flops, a shift register, a multiplexer.
- :mod:`intrepyd.lib.plc`: the standard function blocks of IEC 61131-3, as a
  PLC program uses them — edge detectors (R_TRIG, F_TRIG), bistables (SR, RS)
  and an up counter (CTU).

API convention
--------------

- A **combinational** block is a function ``mk_<name>(ctx, ...) -> net`` that
  returns its output net directly (for example :func:`~intrepyd.lib.eda.mk_mux`).
- A block that **builds its own state and needs no feedback from the caller**
  is also a function; it creates its internal latches and returns the output
  net(s) (for example :func:`~intrepyd.lib.eda.mk_clock`,
  :func:`~intrepyd.lib.eda.mk_counter`, and every block in
  :mod:`intrepyd.lib.plc`).
- A **stateful** block whose next value depends on signals the caller provides
  *after* construction is a **class**: build it, then call ``set_init_next(...)``
  to close the loop (for example :class:`~intrepyd.lib.eda.LatchD`,
  :class:`~intrepyd.lib.eda.Delay`, the flip-flops, and
  :class:`~intrepyd.lib.eda.ShiftRegister`). This two-step shape is what lets a
  component feed back into itself.
"""
