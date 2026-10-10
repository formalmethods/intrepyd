"""
The reusable sub-model A of the composition example (#32 of intrepid-specs).

``StickyAnd`` is an ``intrepyd.circuit.Circuit``: a small circuit with inputs
``x`` and ``y`` and output ``z``, where ``z`` latches true the first cycle in
which ``x`` and ``y`` both hold, and stays true afterwards. It has its own
state (the latch ``z``), so every copy of it keeps its own memory.

A ``Circuit`` can be used two ways:

- on its own, as a top-level model: ``mk_circuit()`` makes ``x`` and ``y`` as
  primary inputs (``_mk_inputs``), builds the body, and tags ``z`` an output;
- as a sub-model inside a larger circuit: the parent calls
  ``mk_naked_circuit(inputs, namespace=True)`` passing the nets to wire into
  ``x`` and ``y``, and gets back ``{'z': ...}`` — no primary inputs are made.

``top.py`` uses it the second way, twice.
"""

from intrepyd.circuit import Circuit


class StickyAnd(Circuit):
    """z := (x and y) ever held; latches true and stays true."""

    def _mk_inputs(self):
        # Only used when StickyAnd is a top-level model (mk_circuit).
        bool_t = self.context.mk_boolean_type()
        self.inputs['x'] = self.context.mk_input('x', bool_t)
        self.inputs['y'] = self.context.mk_input('y', bool_t)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):
        ctx = self.context
        both = ctx.mk_and(inputs['x'], inputs['y'])
        z = ctx.mk_latch('z', ctx.mk_boolean_type())
        ctx.set_latch_init_next(z, ctx.mk_false(), ctx.mk_or(z, both))
        self.nets['both'] = both
        self.nets['z'] = z
        return {'z': z}
