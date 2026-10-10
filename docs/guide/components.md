# Using the component library

`intrepyd.lib` collects reusable building blocks so you assemble a model from
vetted parts instead of rebuilding the same latches, counters and timers. It
has two submodules: [`intrepyd.lib.eda`](../reference/library.md) for
hardware/EDA blocks and [`intrepyd.lib.plc`](../reference/library.md) for the
IEC 61131-3 function blocks a PLC program uses.

## The two shapes

A block is either a function or a class, by a simple rule:

- a **combinational** block, or one that **builds its own state** and needs
  nothing back from you, is a function `mk_<name>(ctx, ...)` returning its
  output net(s) — `mk_mux`, `mk_clock`, `mk_counter`, and every `plc` block;
- a **stateful** block whose next value depends on signals you provide *after*
  construction is a class: build it, then call `set_init_next(...)` to close
  the loop — `LatchD`, `Delay`, `FlipFlopD`, `FlipFlopDE`, `ShiftRegister`.

## EDA example: a shift register

```python
import intrepyd as ip
from intrepyd.lib.eda import ShiftRegister

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()

d = ctx.mk_input('d', bool_t)
sr = ShiftRegister(ctx, 'sr', bool_t, length=3)   # 3-stage register
sr.set_init_next(ctx.mk_false(), d)               # fill with F, shift in d
ctx.mk_output(sr.q)                               # q is d delayed by 3 cycles
```

## PLC example: an up counter

Every `plc` block works on a synchronous scan cycle (one simulation step is one
cycle), and the timers measure their preset time in cycles.

```python
import intrepyd as ip
from intrepyd.lib.plc import mk_ctu

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()
int8_t = ctx.mk_int8_type()

cu = ctx.mk_input('cu', bool_t)        # count-up (counted on its rising edge)
reset = ctx.mk_input('reset', bool_t)
pv = ctx.mk_number('4', int8_t)        # preset value

cv, q = mk_ctu(ctx, 'ctu', cu, reset, pv, int8_t)
ctx.mk_output(q)                       # q is true once cv reaches 4
```

You can then simulate the model (see [Simulating](simulating.md)) or check a
property on it (see [Model checking](model-checking.md)); the counter's `q`
makes a natural target.

## What is in the library

| Module | Blocks |
| ------ | ------ |
| `intrepyd.lib.eda` | `mk_clock`, `mk_counter`, `mk_mux`, `LatchD`, `Delay`, `FlipFlopD`, `FlipFlopDE`, `ShiftRegister` |
| `intrepyd.lib.plc` | `mk_r_trig`, `mk_f_trig`, `mk_sr`, `mk_rs`, `mk_ctu`, `mk_ctd`, `mk_ctud`, `mk_ton`, `mk_tof`, `mk_tp` |

See the [component library reference](../reference/library.md) for the full
signatures and the exact semantics of each block.
