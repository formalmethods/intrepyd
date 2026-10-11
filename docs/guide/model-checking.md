# Model checking

A *target* is a net you ask the engine to make true. Proving a safety property
means showing that its negation is an unreachable target.

Every engine answers with an [`EngineResult`](../reference/engine.md):

| Result        | Meaning                                                        |
| ------------- | -------------------------------------------------------------- |
| `REACHABLE`   | Target reached; `get_last_trace()` returns the counterexample  |
| `UNREACHABLE` | Proof that the target can never be reached                     |
| `UNKNOWN`     | No answer (for plain BMC: nothing found within the bound)      |

## Bounded model checking

BMC looks for a counterexample at exactly the current depth, so it is driven
incrementally from 0 upwards. `REACHABLE` means a counterexample was found;
`UNKNOWN` means none exists **within that bound**, which is not a proof.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int8_t = ctx.mk_int8_type()

c = ctx.mk_latch('c', int8_t)
ctx.set_latch_init_next(c, ctx.mk_number('0', int8_t),
                        ctx.mk_add(c, ctx.mk_number('1', int8_t)))
bad = ctx.mk_eq(c, ctx.mk_number('5', int8_t))

bmc = ctx.mk_bmc()
bmc.add_target(bad)
bmc.add_watch(c)
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
c  0  1  2  3  4  5
```

Call `bmc.set_allow_targets_at_any_depth()` to accept a target that becomes
true anywhere up to the current depth instead of exactly at it.
`mk_optimizing_bmc()` returns a BMC engine backed by the Z3 optimizer, for
finding minimal-cost counterexamples.

## k-induction

BMC can also prove properties, by turning on induction:

```python
bmc = ctx.mk_bmc()
bmc.set_use_induction()
bmc.add_target(target)
for depth in range(100):
    bmc.set_current_depth(depth)
    result = bmc.reach_targets()
    if result != EngineResult.UNKNOWN:
        break                       # REACHABLE or UNREACHABLE, both conclusive
```

## Backward reachability

Backward reachability is unbounded: it can answer `UNREACHABLE`, which *is* a
proof.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()

flag = ctx.mk_latch('flag', bool_t)
ctx.set_latch_init_next(flag, ctx.mk_false(), flag)   # false forever

br = ctx.mk_backward_reach()
br.add_target(flag)
assert br.reach_targets() == EngineResult.UNREACHABLE
```

## IC3/PDR

`mk_pdr()` returns an IC3/PDR engine, built on Spacer, the one of Z3. Like
backward reachability it answers in one call, and can prove a target
unreachable; it does so by finding an inductive invariant, which is often
possible where k-induction and backward reachability get nowhere:

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int_t = ctx.mk_int_type()

c = ctx.mk_latch('c', int_t)
ctx.set_latch_init_next(c, ctx.mk_number('0', int_t),
                        ctx.mk_add(c, ctx.mk_number('1', int_t)))

pdr = ctx.mk_pdr()
pdr.add_target(ctx.mk_eq(c, ctx.mk_number('-1', int_t)))
assert pdr.reach_targets() == EngineResult.UNREACHABLE   # invariant: c >= 0
```

k-induction cannot prove this one, as `-2, -1` is a path that ignores the
initial state, and backward reachability would follow `-1, -2, -3, ...` for
ever. When a target is reachable, the counterexample comes from BMC, so
`get_last_trace()` returns a shortest one.

!!! note "Proofs are checked"
    Before answering `UNREACHABLE`, the engine verifies that the invariant
    found holds initially, is preserved by every step, and excludes the
    targets. If it does not, which can happen with some versions of Z3, the
    answer is `UNKNOWN` rather than a wrong proof.

PDR is at its best on unbounded integers (`mk_int_type()`, or `inttype='int'`
when translating Lustre); it also handles fixed-width integers, but bit-vector
invariants are harder to find.

## Which engine proves what

The engines are complementary, which is what the [portfolio](portfolio.md)
exploits: BMC finds counterexamples fastest, and k-induction, backward
reachability and PDR each prove properties the others cannot.

## Proof certificates

A counterexample can be checked by anyone: simulate it. A proof can be checked
too. Ask an engine for **proof certificates**, and an `UNREACHABLE` answer
comes with the formulas it rests on, as an SMT-LIB 2 script that any SMT
solver can run, so the verdict does not have to be taken on intrepid's word:

```python
pdr = ctx.mk_pdr()
pdr.add_target(ctx.mk_eq(c, ctx.mk_number('-1', int_t)))
pdr.set_produce_certificates()
if pdr.reach_targets() == EngineResult.UNREACHABLE:
    with open('proof.smt2', 'w') as out:
        out.write(pdr.get_last_certificate())
```

```console
$ z3 proof.smt2
unsat
unsat
unsat
```

Each `check-sat` of the script must answer `unsat`. The script defines the
circuit (`Init`, `Assume`, `Trans`, `Bad`) and states, in its header, what the
conditions prove:

- PDR and backward reachability give an **inductive invariant** `Inv`, and
  three conditions: `Inv` holds in the initial states, every step keeps it,
  and it excludes the targets;
- k-induction (`set_use_induction()`) gives its **base cases**, no target in
  0 to k steps, and its **step**, no path of k+1 different states that
  reaches a target only at its last one.

Machine integers are bit-vectors with the signedness of each operator, as
intrepid checked them, so the solver proves exactly the same thing. intrepid
checks every certificate itself before giving it: one that does not hold
turns the answer into `UNKNOWN`. A certificate is only made when asked for,
as the check costs time; plain BMC proves nothing and gives none. A portfolio
gives the certificate of the engine that proved
(`ctx.mk_portfolio(certificates=True)`, then `get_last_certificate()`).

Certificates need intrepid 1.4 or newer: with an older library,
`set_produce_certificates()` raises `RuntimeError`.
