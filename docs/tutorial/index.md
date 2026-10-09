# Tutorial

This is a hands-on walk through intrepyd, from nothing to proving a property of
a real model. Type each snippet along the way: every one is self-contained and
runnable, and each builds on the idea of the last. We carry a single running
example — a counter — from a handful of gates to a formal proof, and only then
leave hand-built circuits behind to translate a model from the outside world.

It assumes intrepyd is installed (see [Installation](../guide/installation.md)).
When a step needs more detail than the story gives, it points into the
[guide](../guide/building-models.md) and the
[API reference](../reference/index.md) rather than repeating it.

## 1. A first netlist

Everything in intrepyd comes from a [`Context`](../reference/context.md): it is
the factory for types, nets, engines and traces. A **net** is a node of the
circuit; an **input** is a net whose value is free, chosen from outside; an
**output** is a net we mark as interesting. Let us make the smallest circuit
there is — an `and` of two inputs:

```python
import intrepyd as ip

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()

a = ctx.mk_input('a', bool_t)
b = ctx.mk_input('b', bool_t)
both = ctx.mk_and(a, b)
ctx.mk_output(both)
```

Nothing has been computed yet: we have only *described* a circuit. `a` and `b`
are nets whose value the world supplies, `both` is a net derived from them, and
`both` is the only output. A net is just a handle — an integer id under the
hood — and it is only ever meaningful inside the context that made it.

!!! tip "Build through the context"
    Always build with the `mk_*` methods of `Context`, never through
    `intrepyd.api` directly: the context records the calls as a *recipe*, which
    is what lets the [portfolio](../guide/portfolio.md) rebuild the circuit in
    another process later.

## 2. Adding state

A combinational net is a function of the current inputs only. To talk about
*time* we need memory: a **latch**. A latch has an **initial** value — what it
holds at step 0 — and a **next** value — what it holds at the following step, as
a function of the current nets. We build a counter that increments every step,
unless a `reset` input brings it back to zero:

```python
import intrepyd as ip

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()
int8_t = ctx.mk_int8_type()

reset = ctx.mk_input('reset', bool_t)
count = ctx.mk_latch('count', int8_t)
ctx.set_latch_init_next(
    count,
    ctx.mk_number('0', int8_t),                                   # init: 0
    ctx.mk_ite(reset,                                             # next:
               ctx.mk_number('0', int8_t),                        #   0 if reset
               ctx.mk_add(count, ctx.mk_number('1', int8_t))))    #   else count + 1
```

`set_latch_init_next(latch, init, next)` wires the two together. Note that the
*next* value may mention the latch itself (`count` on the right-hand side): that
is the step from one state to the next. Constants always come from
`mk_number(value, type)`, with the value as a string.

## 3. Simulating it

The quickest way to see a circuit move is to *simulate* it: give the inputs
concrete values over time with a [`Trace`](../reference/trace.md), run the
[`Simulator`](../reference/simulator.md), and read back the nets we watch.

```python
trace = ctx.mk_trace()
pattern = ['false', 'false', 'true', 'false', 'false']   # reset at step 2
for depth, value in enumerate(pattern):
    trace.set_value(reset, depth, value)

simulator = ctx.mk_simulator()
simulator.add_watch(count)
simulator.simulate(trace, 4)

print(trace.get_as_dataframe(ctx.net2name))
```

```text
        0  1  2  3  4
reset   F  F  T  F  F
count   0  1  2  0  1
```

Read it left to right as time. `count` starts at its init, `0`, and climbs with
each step; the `reset` at step 2 takes effect on the *following* value, so
`count` drops to `0` at step 3 and resumes. Booleans print as `T` / `F`, and a
`?` (none here) marks a net the engine left free. This is the whole idea of a
step: the value at step *d+1* is the latch's *next*, computed from the nets at
step *d*.

## 4. Asking a question

Simulation answers "what happens for *this* input?". Verification answers "does
there exist *any* input that makes something happen?". You ask by turning an
expectation into a **target**: a net the engine tries to make true. Suppose we
expect that the counter never reaches 5. The engine's job is to look for a
counterexample, so the target is the negation — "`count` equals 5":

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
bool_t, int8_t = ctx.mk_boolean_type(), ctx.mk_int8_type()

reset = ctx.mk_input('reset', bool_t)
count = ctx.mk_latch('count', int8_t)
ctx.set_latch_init_next(
    count, ctx.mk_number('0', int8_t),
    ctx.mk_ite(reset, ctx.mk_number('0', int8_t),
               ctx.mk_add(count, ctx.mk_number('1', int8_t))))

bad = ctx.mk_eq(count, ctx.mk_number('5', int8_t))

bmc = ctx.mk_bmc()
bmc.add_target(bad)
bmc.add_watch(count)
for depth in range(20):
    bmc.set_current_depth(depth)
    if bmc.reach_targets() == EngineResult.REACHABLE:
        print(f'counterexample at depth {depth}')
        print(bmc.get_last_trace().get_as_dataframe(ctx.net2name))
        break
```

```text
counterexample at depth 5
         0  1  2  3  4  5
reset    F  F  F  F  F  F
count    0  1  2  3  4  5
```

[Bounded model checking](../guide/model-checking.md#bounded-model-checking)
(BMC) searches for a counterexample at a given depth, so we drive it from `0`
upward. It is free to pick the inputs, and it found the shortest witness:
hold `reset` false for five steps and `count` reaches `5`. `get_last_trace()`
returns that counterexample as a trace, which we read exactly as in step 3.

Now make the property *hold* and watch what BMC can and cannot say. Our counter
never goes negative, so ask instead for `count == -1`:

```python
unreachable = ctx.mk_eq(count, ctx.mk_number('-1', int8_t))

bmc = ctx.mk_bmc()
bmc.add_target(unreachable)
for depth in range(20):
    bmc.set_current_depth(depth)
    print(depth, bmc.reach_targets())
```

```text
0 EngineResult.UNKNOWN
1 EngineResult.UNKNOWN
...
19 EngineResult.UNKNOWN
```

BMC answers `UNKNOWN` at every depth: it found no counterexample *within the
bound*. That is **not a proof** — it only means none exists up to depth 19. (On
`int8` the counter would in fact wrap around to `-1` after many steps; to prove
a real "never negative" we need both an engine that reasons about all depths at
once and a type without wraparound. Both come next.)

## 5. Proving it

To prove, not just search, we switch to engines that can answer `UNREACHABLE`,
and to **unbounded integers** (`mk_int_type()`), the mathematical integers that
never overflow — which also makes the engines' job far easier. Here is the same
counter, now unbounded and free-running, with the property "`count` is never
`-1`":

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int_t = ctx.mk_int_type()

count = ctx.mk_latch('count', int_t)
ctx.set_latch_init_next(count, ctx.mk_number('0', int_t),
                        ctx.mk_add(count, ctx.mk_number('1', int_t)))
target = ctx.mk_eq(count, ctx.mk_number('-1', int_t))

pdr = ctx.mk_pdr()
pdr.add_target(target)
assert pdr.reach_targets() == EngineResult.UNREACHABLE      # invariant: count >= 0
```

[IC3/PDR](../guide/model-checking.md#ic3pdr) proves it by discovering the
*inductive invariant* `count >= 0`: true at the start, preserved by every step,
and incompatible with the target. Every proof it returns is independently
checked, so a wrong proof becomes `UNKNOWN` rather than a false verdict.

The three proving engines are complementary, and this example tells them apart:

- **k-induction** (`mk_bmc()` with `set_use_induction()`) cannot prove it: the
  two-state path `-2, -1` satisfies the step relation while ignoring the initial
  state, so induction fails without the invariant.
- **Backward reachability** (`mk_backward_reach()`) would walk back from `-1`
  through `-2, -3, …` for ever, never closing.
- **PDR** finds the invariant and closes in one call.

Rather than guess which engine suits a problem, run them together with the
[portfolio](../guide/portfolio.md). Each engine runs in its own process, and the
first conclusive answer wins:

```python
if __name__ == '__main__':                 # required: the portfolio uses multiprocessing
    portfolio = ctx.mk_portfolio()
    portfolio.add_target(target)
    result = portfolio.reach_targets(timeout=60)
    print(result, 'proved by', portfolio.get_last_engine())
```

```text
EngineResult.UNREACHABLE proved by pdr
```

## 6. Translating a real model

Hand-built circuits are how intrepyd thinks, but real work starts from models in
other languages. The translators in [`intrepyd.tools`](../reference/tools.md)
turn such a model into exactly the kind of circuit we have been building — same
nets, same engines, same traces. We use the Lustre model shipped with intrepyd,
`intrepyd/tests/lustre/peterson_1.lus`, an encoding of Peterson's mutual
exclusion protocol whose top node exposes a property `OK`:

```python
import intrepyd as ip
from intrepyd.tools import translate_lustre
from intrepyd.engine import EngineResult

encoding = translate_lustre('intrepyd/tests/lustre/peterson_1.lus',
                            'top', 'real', 'encoding')

ctx = ip.Context()
circuit = encoding.mk_instance(ctx, 'peterson')
circuit.mk_circuit()

br = ctx.mk_backward_reach()
br.add_target(ctx.mk_not(circuit.outputs['OK']))
print(br.reach_targets())
```

```text
EngineResult.UNREACHABLE
```

`translate_lustre` writes a python module (`encoding.py`) with a
[`Circuit`](../reference/circuit.md) subclass; `mk_instance(...).mk_circuit()`
builds it in our context, and from there it is an ordinary circuit. The target
is "`OK` fails", and `UNREACHABLE` is a proof that it never does — mutual
exclusion holds. The same `tools` module translates
[IEC 61131-3 Structured Text](../guide/importing.md#iec-61131-3-structured-text-plcopen-xml)
and [Simulink](../guide/importing.md#simulink) models the same way.

### Why the encoding matters

The third and fourth arguments of `translate_lustre` choose how Lustre's `real`
and `int` are encoded, and the choice can change the verdict. Take a one-line
property — "if `x >= 0` then `x + 1 > 0`":

```lustre
node top(x : int) returns (OK : bool);
let
    OK = x >= 0 => x + 1 > 0;
    --%PROPERTY OK;
    --%MAIN;
tel
```

With `inttype='int'` (unbounded integers) the property is proved; with
`inttype='int32'` (32-bit machine integers) backward reachability finds the
counterexample `x = 2147483647`, where `x + 1` overflows to a negative number.
Same model, two faithful encodings, opposite answers — which is why, when you
can, you reason on unbounded integers, as we did in step 5.

## Where to go next

You have built a circuit from gates and latches, simulated it, refuted a
property with a counterexample, proved one with an inductive invariant, run the
engines as a portfolio, and translated and verified a real model — the whole
arc of intrepyd. From here:

- the [guide](../guide/building-models.md) covers each task in full: all the
  [types and operators](../guide/building-models.md), the
  [engines](../guide/model-checking.md), [importing models](../guide/importing.md),
  [benchmarking](../guide/benchmarking.md) and [running as a service](../guide/service.md);
- the [API reference](../reference/index.md) documents every method of
  [`Context`](../reference/context.md), the engines and the traces;
- the models under `intrepyd/tests/` and `benchmarks/` are more circuits to
  simulate and prove.
