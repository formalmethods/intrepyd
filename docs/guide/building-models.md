# Building models

A [`Context`](../reference/context.md) is the factory for everything: types,
nets, engines and traces. Models are circuits made of **inputs**, **latches**
(state, i.e. memory elements) and combinational **nets**.

```python
import intrepyd as ip

ctx = ip.Context()

# Types
bool_t = ctx.mk_boolean_type()
int8_t = ctx.mk_int8_type()
# also: int16/int32/int64, uint8/uint16/uint32/uint64,
#       real, int, float16/float32/float64

# Combinational logic
a = ctx.mk_input('a', bool_t)
b = ctx.mk_input('b', bool_t)
and_gate = ctx.mk_and(a, b)
ctx.mk_output(and_gate)

# State: a latch that starts at 0 and increments whenever b holds
counter = ctx.mk_latch('counter', int8_t)
ctx.set_latch_init_next(
    counter,
    ctx.mk_number('0', int8_t),
    ctx.mk_ite(b, ctx.mk_add(counter, ctx.mk_number('1', int8_t)), counter))
```

## Types

| Category         | Constructors                                                      |
| ---------------- | ----------------------------------------------------------------- |
| Boolean          | `mk_boolean_type`                                                 |
| Signed integers  | `mk_int8_type`, `mk_int16_type`, `mk_int32_type`, `mk_int64_type` |
| Unsigned integers| `mk_uint8_type`, `mk_uint16_type`, `mk_uint32_type`, `mk_uint64_type` |
| Unbounded integer| `mk_int_type` (mathematical integers, no overflow)                |
| Reals            | `mk_real_type` (exact rationals)                                  |
| Floating point   | `mk_float16_type`, `mk_float32_type`, `mk_float64_type` (IEEE 754)|

## Operators

The usual operators are available as `mk_*` methods:

- **logic:** `mk_not`, `mk_and`, `mk_or`, `mk_xor`, `mk_iff`;
- **arithmetic:** `mk_add`, `mk_sub`, `mk_mul`, `mk_div`, `mk_mod`, `mk_minus`;
- **comparison:** `mk_eq`, `mk_neq`, `mk_leq`, `mk_lt`, `mk_geq`, `mk_gt`;
- **choice:** `mk_ite`;
- **casts:** the `mk_cast_to_*` family.

Constants come from `mk_number(value, type)`, where `value` is a string; see
the [`Context` reference](../reference/context.md) for the accepted forms.

## Assumptions

`ctx.mk_assumption(net)` constrains the search to states where `net` holds, so
that every engine ignores the states the assumption rules out.

## Larger models

Larger models are usually built by subclassing
[`intrepyd.circuit.Circuit`](../reference/circuit.md) and implementing
`_mk_inputs` and `_mk_naked_circuit_impl`; this is what the Lustre and
Structured Text translators generate. See [Importing models](importing.md).

!!! warning "Build circuits through the `Context`"
    Each context records the calls that build its circuit, as a *recipe*, so
    that the [portfolio](portfolio.md) can rebuild it in another process. A
    circuit must therefore be built through the methods of `Context`, not
    through `intrepyd.api` directly.
