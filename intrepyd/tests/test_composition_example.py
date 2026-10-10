"""
Tests the model-composition example (#32 of intrepid-specs): the two copies of
the sub-model keep independent state. It imports the example the way the guide
tells users to — from its own directory — by putting that directory on the
path.
"""

import os
import sys
import unittest

import intrepyd as ip

_EXAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            os.pardir, 'examples', 'composition')
if _EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, _EXAMPLE_DIR)

from top import Top  # noqa: E402  (needs the path tweak above)


class TestCompositionExample(unittest.TestCase):
    def test_two_copies_keep_independent_state(self):
        ctx = ip.Context()
        top = Top(ctx, 'top')
        top.mk_circuit()

        a, b = top.inputs['a'], top.inputs['b']
        c, d = top.inputs['c'], top.inputs['d']
        left_z, right_z = top.nets['left_z'], top.nets['right_z']

        tr = ctx.mk_trace()
        # left sees a&b at t1 (so it sticks); right never sees c&d
        tr.set_value(a, 0, 'F'); tr.set_value(b, 0, 'F')
        tr.set_value(a, 1, 'T'); tr.set_value(b, 1, 'T')
        tr.set_value(a, 2, 'F'); tr.set_value(b, 2, 'F')
        for t in range(3):
            tr.set_value(c, t, 'T' if t == 0 else 'F')  # c,d never both true
            tr.set_value(d, t, 'F')

        simulator = ctx.mk_simulator()
        simulator.add_watch(left_z)
        simulator.add_watch(right_z)
        simulator.simulate(tr, 3)

        # left latched true after a&b (t2) and stays true; right never fires
        self.assertEqual('F', tr.get_value(left_z, 0))
        self.assertEqual('F', tr.get_value(left_z, 1))
        self.assertEqual('T', tr.get_value(left_z, 2))
        self.assertEqual('T', tr.get_value(left_z, 3))
        for t in range(4):
            self.assertEqual('F', tr.get_value(right_z, t))


if __name__ == '__main__':
    unittest.main()
