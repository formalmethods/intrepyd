"""
The top model B of the composition example (#32 of intrepid-specs): it imports
the sub-model A (``StickyAnd``) and instantiates it **twice**, as two
independent copies ``left`` and ``right``, wired to different inputs.

File layout — the important part
--------------------------------
A model is ordinary python. For ``from submodel import StickyAnd`` to work,
``submodel.py`` must be importable, the simplest way being to keep it **in the
same directory** as ``top.py`` (as here) and run from that directory::

    cd intrepyd/examples/composition
    python top.py                     # build it
    python -m intrepyd.export top.py  # export its netlist (roadmap #28)

Run from elsewhere and the import fails, because that directory is not on the
import path. If you prefer to keep the models in a package, put an
``__init__.py`` next to them and import ``from mypkg.submodel import StickyAnd``,
with the package's parent on ``PYTHONPATH``.

Each copy of ``StickyAnd`` is built with ``mk_naked_circuit(inputs,
namespace=True)``: ``namespace=True`` prefixes every net the copy creates with
the copy's name (``left.z``, ``right.z``), so the two copies' nets never clash
even though both call their latch ``z``.
"""

from intrepyd.circuit import Circuit
from submodel import StickyAnd


class Top(Circuit):
    """result = left.z or right.z, with two independent StickyAnd copies."""

    def _mk_inputs(self):
        bool_t = self.context.mk_boolean_type()
        for name in ('a', 'b', 'c', 'd'):
            self.inputs[name] = self.context.mk_input(name, bool_t)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):
        ctx = self.context

        # First copy of A, fed by (a, b)
        left = StickyAnd(ctx, 'left')
        left_out = left.mk_naked_circuit({'x': inputs['a'], 'y': inputs['b']}, namespace=True)

        # Second, independent copy of A, fed by (c, d)
        right = StickyAnd(ctx, 'right')
        right_out = right.mk_naked_circuit({'x': inputs['c'], 'y': inputs['d']}, namespace=True)

        self.nets['left_z'] = left_out['z']
        self.nets['right_z'] = right_out['z']
        result = ctx.mk_or(left_out['z'], right_out['z'])
        self.nets['result'] = result
        return {'result': result}


if __name__ == '__main__':
    import intrepyd as ip

    context = ip.Context()
    top = Top(context, 'top')
    top.mk_circuit()
    print('Built B with two copies of A. Nets:', ', '.join(sorted(top.nets)))
