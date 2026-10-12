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

## From a circuit diagram

A circuit drawn in the intrepid-vscode editor (a diagram, see
`intrepyd.diagram`) needs no `Circuit` subclass and no list of conditions: a
decision is a block, and its conditions are found by walking back from it
through the boolean operators (and, or, not, xor, iff, implies, ite) and the
pins of sub-systems, down to the first nets that are none of them — inputs,
latches, comparisons, the outputs of library blocks. Constants are not
conditions; a net met twice is one condition; `stops` makes a block a
condition, so the walk ends there.

For `(a and b) or c`:

```python
from intrepyd import diagram

doc = {
    "format": "intrepyd-diagram", "version": 3, "layout": {"blocks": {}},
    "circuit": {
        "nodes": [
            {"id": 1, "kind": "input", "name": "a", "type": "bool"},
            {"id": 2, "kind": "input", "name": "b", "type": "bool"},
            {"id": 3, "kind": "input", "name": "c", "type": "bool"},
            {"id": 4, "kind": "gate", "name": "and1", "op": "and"},
            {"id": 5, "kind": "gate", "name": "or1", "op": "or"},
        ],
        "edges": [
            {"from": 1, "to": 4, "port": "a"}, {"from": 2, "to": 4, "port": "b"},
            {"from": 4, "to": 5, "port": "a"}, {"from": 3, "to": 5, "port": "b"},
        ],
    },
}

if __name__ == "__main__":            # the engines run in processes of their own
    print([c["name"] for c in diagram.conditions(doc, 5)])
    [result] = diagram.mcdc(doc, decisions=[5])["results"]
    for cond in result["conditions"]:
        print(cond["name"], cond["status"], cond["pair"])
    for i, test in enumerate(result["tests"]):
        print(i, test["conditions"], test["decision"])
```

prints

```text
['a', 'b', 'c']
a covered [0, 1]
b covered [2, 0]
c covered [3, 4]
0 ['T', 'T', 'F'] T
1 ['F', 'T', 'F'] F
2 ['T', 'F', 'F'] F
3 ['F', 'F', 'F'] F
4 ['F', 'F', 'T'] T
```

Each condition has its pair of tests: they differ in the condition and in the
decision, and in each the condition decides the outcome (masking MC/DC). A test
is a run of the circuit — its inputs at each step, as a simulation takes them,
and every block's values along it — and its conditions and decision are read at
its last step, so a condition on a latch gets a test long enough to set it. A
condition with no pair is `unreachable` (masked, or redundant logic), or
`unknown` when none is found within `depth` steps and `timeout` seconds. The
tests are not a minimal set (here five, where four would do).

`python -m intrepyd.diagram mcdc FILE` does the same from the command line, for
the decisions of the diagram's `testgen` section or `--decision ID`, and prints
the result as JSON; it is what the editor runs.

## Notes

- Keep the circuit small: `compute_mcdc` duplicates it and runs the model
  checker on each objective, so cost grows with the circuit and `max_depth`.
- Conditions that are themselves inputs (as `A` and `B` here) are registered in
  `self.nets` by `_mk_inputs`; internal nets used as decisions or conditions
  must be added in `_mk_naked_circuit_impl`.
