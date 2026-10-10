# Composing models

A model can be **imported into another model** and instantiated several times,
so you build a reusable sub-model once and wire copies of it into a larger one.
The copies keep their nets — and their state — apart.

A reusable model is a [`Circuit`](../reference/circuit.md) subclass. The parent
builds each copy with `mk_naked_circuit(inputs, namespace=True)`: it passes the
nets to wire into the sub-model's inputs, gets back the sub-model's outputs, and
`namespace=True` prefixes every net the copy creates with the copy's name, so
two copies that both call a latch `z` become `left.z` and `right.z` — no clash.

## The sub-model A

```python
# submodel.py
from intrepyd.circuit import Circuit

class StickyAnd(Circuit):
    """z latches true the first cycle x and y both hold, and stays true."""

    def _mk_inputs(self):                       # only for standalone use
        bool_t = self.context.mk_boolean_type()
        self.inputs['x'] = self.context.mk_input('x', bool_t)
        self.inputs['y'] = self.context.mk_input('y', bool_t)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):   # used when composed
        ctx = self.context
        both = ctx.mk_and(inputs['x'], inputs['y'])
        z = ctx.mk_latch('z', ctx.mk_boolean_type())
        ctx.set_latch_init_next(z, ctx.mk_false(), ctx.mk_or(z, both))
        self.nets['z'] = z
        return {'z': z}
```

## The model B, importing two copies of A

```python
# top.py
from intrepyd.circuit import Circuit
from submodel import StickyAnd

class Top(Circuit):
    def _mk_inputs(self):
        bool_t = self.context.mk_boolean_type()
        for name in ('a', 'b', 'c', 'd'):
            self.inputs[name] = self.context.mk_input(name, bool_t)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):
        ctx = self.context
        left = StickyAnd(ctx, 'left')
        left_out = left.mk_naked_circuit({'x': inputs['a'], 'y': inputs['b']}, namespace=True)
        right = StickyAnd(ctx, 'right')
        right_out = right.mk_naked_circuit({'x': inputs['c'], 'y': inputs['d']}, namespace=True)
        result = ctx.mk_or(left_out['z'], right_out['z'])
        self.nets['result'] = result
        return {'result': result}
```

`left` and `right` each build their own latch; because of the namespaces the two
are independent, so `left` sticking true does not affect `right`.

## Where to put the files

A model is ordinary python, so composition is just an `import`. The simplest
layout is **both files in the same directory**, and run from there:

```bash
cd your/models            # the directory holding submodel.py and top.py
python top.py             # from here, "from submodel import StickyAnd" resolves
python -m intrepyd.export top.py   # the exporter (roadmap #28) finds it too
```

The import works because python puts the script's own directory on the import
path. Run `python path/to/top.py` **from another directory** and the import
still resolves (the script's directory is used), but a bare
`python -c "import top"` from elsewhere does not — the directory is not on the
path. If you prefer a package, add an `__init__.py` next to the models and
import `from mypkg.submodel import StickyAnd`, with the package's parent on
`PYTHONPATH`. Avoid naming a model file after a standard or installed module
(e.g. `types.py`, `queue.py`), which would shadow it.

## Runnable example

A complete, tested version of this example is in the repository under
`intrepyd/examples/composition/` (`submodel.py` and `top.py`), exercised by
`tests/test_composition_example.py`.
