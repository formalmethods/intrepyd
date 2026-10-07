"""
Tests of the Simulink front-end, translate_simulink(). They need its library,
which is closed source and released on its own: they are skipped without it.
To run them on a local build of it, point INTREPID_SIMULINK_LIBRARY at the
library, e.g. ../intrepid-simulink/build/libintrepid_simulink.so.
"""

import os
import sys
import tempfile
import unittest

import intrepyd
from intrepyd import simulink
from intrepyd import tools
from intrepyd.engine import EngineResult

# out = pre(out) + in, from 0, and an assertion that out stays below limit
COUNTER = """
Model {
  Name "counter"
  System {
    Name "counter"
    Block {
      BlockType Inport
      Name "in"
      OutDataTypeStr "int8"
    }
    Block {
      BlockType Sum
      Name "Add"
      Inputs "++"
    }
    Block {
      BlockType UnitDelay
      Name "Delay"
    }
    Block {
      BlockType Outport
      Name "out"
    }
    Block {
      BlockType Constant
      Name "Limit"
      Value "limit"
    }
    Block {
      BlockType RelationalOperator
      Name "Below"
      Operator "<"
    }
    Block {
      BlockType Assertion
      Name "Check"
    }
    Line {
      SrcBlock "in"
      SrcPort 1
      DstBlock "Add"
      DstPort 1
    }
    Line {
      SrcBlock "Delay"
      SrcPort 1
      DstBlock "Add"
      DstPort 2
    }
    Line {
      SrcBlock "Add"
      SrcPort 1
      Branch {
        DstBlock "Delay"
        DstPort 1
      }
      Branch {
        DstBlock "out"
        DstPort 1
      }
      Branch {
        DstBlock "Below"
        DstPort 1
      }
    }
    Line {
      SrcBlock "Limit"
      SrcPort 1
      DstBlock "Below"
      DstPort 2
    }
    Line {
      SrcBlock "Below"
      SrcPort 1
      DstBlock "Check"
      DstPort 1
    }
  }
}
"""


def _available():
    try:
        return simulink.library_path() is not None
    except ImportError:
        return False


@unittest.skipUnless(_available(), 'the Simulink front-end library is not available')
class TestSimulink(unittest.TestCase):
    """translate_simulink() on a small model, written as a .mdl file"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.model = os.path.join(self.tmp.name, 'counter.mdl')
        with open(self.model, 'w', encoding='utf-8') as model:
            model.write(COUNTER)
        sys.path.insert(0, self.tmp.name)
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        sys.path.remove(self.tmp.name)
        sys.modules.pop('counter_encoding', None)
        self.tmp.cleanup()

    def _circuit(self, limit):
        enc = tools.translate_simulink(self.model, 'counter_encoding', variables={'limit': limit})
        ctx = intrepyd.Context()
        circuit = enc.mk_instance(ctx, 'counter')
        circuit.mk_circuit()
        return ctx, circuit

    def test_it_translates_and_simulates(self):
        """The circuit computes what the model does"""
        ctx, circuit = self._circuit('int8(100)')
        trace = ctx.mk_trace()
        for step, value in enumerate(['3', '4', '-2']):
            trace.set_value(circuit.inputs['in'], step, value)
        simulator = ctx.mk_simulator()
        simulator.add_watch(circuit.outputs['out'])
        simulator.simulate(trace, 2)
        values = [trace.get_value(circuit.outputs['out'], k) for k in range(3)]
        self.assertEqual(['3', '7', '5'], values)

    def test_the_assertion_is_a_target(self):
        """An assertion that can fail is a target that can be reached"""
        ctx, circuit = self._circuit('int8(10)')
        bmc = ctx.mk_bmc()
        bmc.add_target(circuit.targets['counter/Check'])
        self.assertEqual(EngineResult.REACHABLE, bmc.reach_targets())

    def test_it_refuses_what_it_cannot_translate(self):
        """A model that cannot be translated raises, and writes no module"""
        with self.assertRaises(simulink.SimulinkError) as error:
            tools.translate_simulink(self.model, 'counter_encoding')
        self.assertIn('unknown variable limit', str(error.exception))
        self.assertFalse(os.path.exists('counter_encoding.py'))


class TestLibraryLookup(unittest.TestCase):
    """Where the library is looked for"""

    def test_a_wrong_path_is_reported(self):
        """INTREPID_SIMULINK_LIBRARY must be the path of a file"""
        saved = os.environ.get('INTREPID_SIMULINK_LIBRARY')
        os.environ['INTREPID_SIMULINK_LIBRARY'] = '/no/such/library.so'
        try:
            with self.assertRaises(ImportError):
                simulink.library_path()
        finally:
            if saved is None:
                del os.environ['INTREPID_SIMULINK_LIBRARY']
            else:
                os.environ['INTREPID_SIMULINK_LIBRARY'] = saved


if __name__ == '__main__':
    unittest.main()
