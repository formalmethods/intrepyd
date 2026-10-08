# Simulating models

A [`Trace`](../reference/trace.md) holds input values over time. The
[`Simulator`](../reference/simulator.md) propagates them through the circuit
and fills in the watched nets.

```python
import intrepyd as ip

ctx = ip.Context()
bool_t, int8_t = ctx.mk_boolean_type(), ctx.mk_int8_type()

tick = ctx.mk_input('tick', bool_t)
count = ctx.mk_latch('count', int8_t)
ctx.set_latch_init_next(
    count,
    ctx.mk_number('0', int8_t),
    ctx.mk_ite(tick, ctx.mk_add(count, ctx.mk_number('1', int8_t)), count))

trace = ctx.mk_trace()
for depth in range(5):
    trace.set_value(tick, depth, 'true' if depth % 2 == 0 else 'false')

simulator = ctx.mk_simulator()
simulator.add_watch(count)
simulator.simulate(trace, 4)

print(trace.get_as_dataframe(ctx.net2name))
```

```text
       0  1  2  3  4
tick   T  F  T  F  T
count  0  1  1  2  2
```

Booleans are `T` / `F`, and `?` marks a value the engine left unconstrained.

## Traces as data

Traces are also available as plain dictionaries via `get_as_net_dictionary()`
and `get_as_depth_dictionary()`, and can be round-tripped through pandas with
`get_as_dataframe()` and `set_from_dataframe()`.
[`intrepyd.tools.simulate()`](../reference/tools.md) wraps this into a
CSV-driven workflow, and [`intrepyd.plots`](../reference/helpers.md) draws a
trace as a timing diagram.
