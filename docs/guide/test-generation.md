# Automated test generation (MC/DC)

intrepyd can generate **MC/DC** (Modified Condition / Decision Coverage) tests
for a circuit. For every *decision* (a boolean expression) and each of its
*conditions* (the atomic boolean sub-expressions), MC/DC asks for a pair of
tests showing that the condition, on its own, flips the decision: the two tests
differ in that one condition, agree on the others, and the decision differs.
Such a pair is an *independence pair*.

## Describe the circuit

The circuit is a subclass of [`Circuit`](../reference/circuit.md) — the same
class the translators use. Build the inputs in `_mk_inputs`, the body in
`_mk_naked_circuit_impl`, and **register every decision and condition net, by
name, in `self.nets`**: that is how the generator finds them.

```python
import intrepyd as ip
from intrepyd.circuit import Circuit
from intrepyd.atg import compute_mcdc, get_tables_as_dataframe


class And2(Circuit):
    """O = A and B — A and B are the conditions, O is the decision."""

    def _mk_inputs(self):
        bool_t = self.context.mk_boolean_type()
        self.inputs['A'] = self.context.mk_input('A', bool_t)
        self.inputs['B'] = self.context.mk_input('B', bool_t)
        self.nets.update(self.inputs)          # conditions must be in self.nets

    def _mk_naked_circuit_impl(self, inputs):
        out = self.context.mk_and(inputs['A'], inputs['B'])
        self.nets['O'] = out                   # the decision, by name
        return {'O': out}
```

## Generate the tests

Name the decisions and their conditions, then call `compute_mcdc`. It builds the
circuit twice (as `InstA` and `InstB`, each in its own namespace), and searches
with the engines up to `max_depth` for each independence pair.

```python
ctx = ip.Context()
decisions = {'O': ['A', 'B']}          # decision O has conditions A and B

tables, independence_pairs, unreachable = compute_mcdc(ctx, And2, decisions, max_depth=10)

print(get_tables_as_dataframe(tables)['O'])
```

The result is a triple:

- `tables` — the raw MC/DC table per decision; `get_tables_as_dataframe` turns
  it into a pandas `DataFrame` (one column per condition, plus the decision);
- `independence_pairs` — for each condition, the two test rows that form its
  independence pair;
- `unreachable` — the conditions whose objective could not be reached (none, for
  a plain AND).

For an AND gate the table has three distinct tests, and both conditions get an
independence pair. A larger worked example (a six-condition circuit) is in
`intrepyd/tests/test_atg.py`, which doubles as the test suite for the feature.

## Notes

- Keep the circuit small: `compute_mcdc` duplicates it and runs the model
  checker on each objective, so cost grows with the circuit and `max_depth`.
- Conditions that are themselves inputs (as `A` and `B` here) are registered in
  `self.nets` by `_mk_inputs`; internal nets used as decisions or conditions
  must be added in `_mk_naked_circuit_impl`.
