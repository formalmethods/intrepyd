# Importing models

Rather than building circuits by hand, you can translate existing models. The
translators in [`intrepyd.tools`](../reference/tools.md) emit a python module
that you then import and instantiate.

## Lustre

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
print(br.reach_targets())      # EngineResult.UNREACHABLE -- property proved
```

The third argument selects how Lustre `real` is encoded: `'real'` for exact
rationals, or `'float32'` / `'float64'` for floating point.

The `inttype` argument selects how Lustre `int` is encoded:

| `inttype`                      | Encoding                                                     |
| ------------------------------ | ------------------------------------------------------------ |
| `'int32'` (default)            | 32-bit machine integers, as bit-vectors: arithmetic can overflow |
| `'int'`                        | Unbounded integers, the semantics of Lustre itself           |
| `'int8'`, `'int16'`, `'int64'` | Machine integers of that width                               |

```python
encoding = translate_lustre('model.lus', 'top', 'real', 'encoding', inttype='int')
```

The two encodings can give different verdicts. With `x >= 0 => x + 1 > 0`, for
instance, `'int'` proves the property, while `'int32'` finds the
counterexample `x = 2147483647`, where `x + 1` overflows. Unbounded integers
are also much easier for the engines: on the Kind2 benchmarks shipped in
`benchmarks/`, with a 10-second timeout, k-induction solves 617 of the 848
models with `'int'` against 495 with `'int32'`, and backward reachability 665
against 382.

## IEC 61131-3 Structured Text (PLCopen XML)

```python
from intrepyd.tools import translate_iec61131

encoding = translate_iec61131('intrepyd/tests/openplc/simple1.xml', 'encoding')
```

## Simulink

```python
import intrepyd as ip
from intrepyd.tools import translate_simulink
from intrepyd.engine import EngineResult

encoding = translate_simulink('model.slx', 'encoding', variables={'limit': 'int32(10)'})

ctx = ip.Context()
circuit = encoding.mk_instance(ctx, 'model')
circuit.mk_circuit()

bmc = ctx.mk_bmc()
for name, target in circuit.targets.items():  # one per Assertion block
    bmc.add_target(target)
print(bmc.reach_targets())
```

A `.mdl` or `.slx` model is read without MATLAB, with the models its Model
blocks refer to. Its root Inport and Outport blocks are the inputs and outputs
of the circuit; its targets are its Assertion blocks, each reached when its
assertion fails, and the errors that would stop a simulation of its Stateflow
charts: a division by zero, a state inconsistency, a conversion out of range.
`circuit.nets` tells, for each state of each chart (named
`block path:state path`), whether the state is active after the step, for
coverage and for comparisons with Simulink.

The MATLAB workspace the model needs is filled as Simulink fills it: by the
callbacks of the model (`PreLoadFcn` and the others), with their `load` of MAT
files, `Simulink.Bus` objects included, and the scripts they run; then by
`mats=[...]`, MAT files, `scripts=[...]`, MATLAB scripts of assignments, and
`variables`, MATLAB expressions; `callbacks=False` skips the callbacks.
`realtype='real'` translates single and double as reals, not exact but much
easier for the engines, instead of floats. What the translator does not support
is refused with `intrepyd.simulink.SimulinkError`, listing each block that
cannot be translated, never translated approximately.

!!! info "The Simulink front-end is a separate library"
    The translator is a closed-source library, `libintrepid_simulink`, from the
    [intrepid-simulink](https://github.com/formalmethods/intrepid-simulink)
    repository; it is not bundled yet. To use a local build, point
    `INTREPID_SIMULINK_LIBRARY` at it. It translates discrete, single-rate
    models made of the common blocks of arithmetic, logic, delays and routing
    (subsystems, Goto and From, Mux and Demux, buses, Model blocks), and
    Stateflow charts with the C action language and without events, in `.mdl`
    files; Stateflow charts in `.slx` files and MATLAB Function blocks are not
    supported yet.

## Intrepid's own syntax

[`intrepyd.parser.Parser`](../reference/parser.md) reads circuits written in a
line-based syntax, one net per line, `<name> = <operator> <arguments>`, and
returns a populated `Context`:

```text
i1 = input bool
i2 = input bool
a1 = and i1 i2
l1 = latch bool
set_latch_init_next l1 true false
n0 = number 0 int8
```

```python
from intrepyd.parser import Parser

ctx = Parser().parse_file('model.txt')      # or parse_stream(stream)
target = ctx.nets['a1']
```

A line that does not parse raises `intrepyd.parser.ParseError`, with the line
number. The upload route of the REST service takes the same syntax.
