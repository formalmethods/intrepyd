from intrepyd.lustre2py import translator
from intrepyd.context import Context
from intrepyd.engine import EngineResult
import importlib
import importlib.util
import tempfile
import time
import unittest
import os
from . import from_fixture_path

class TestLustre(unittest.TestCase):
    def test_it_translates(self):
        module = 'encoding'
        outfile = module + '.py'
        translator.translate(from_fixture_path('lustre/peterson_1.lus'), 'top', outfile, 'real')
        time.sleep(1) # Give some extra time to write encoding.py to a file
        enc = importlib.import_module(module)
        ctx = Context()
        circ = enc.mk_instance(ctx, 'test')
        circ.mk_circuit()
        self.assertTrue('OK' in circ.outputs)
        os.remove(outfile)

    def _translate_and_reach(self, source, inttype):
        """Proves or refutes OK in a lustre program, with the given int encoding"""
        with tempfile.TemporaryDirectory() as tmp:
            lus = os.path.join(tmp, 'program.lus')
            out = os.path.join(tmp, 'program_encoding.py')
            with open(lus, 'w', encoding='utf-8') as lus_file:
                lus_file.write(source)
            translator.translate(lus, 'top', out, 'real', inttype)
            spec = importlib.util.spec_from_file_location('program_encoding', out)
            enc = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(enc)
        ctx = Context()
        circ = enc.mk_instance(ctx, 'test')
        circ.mk_circuit()
        br = ctx.mk_backward_reach()
        br.add_target(ctx.mk_not(circ.outputs['OK']))
        return br.reach_targets()

    def test_int_encodings(self):
        # Holds on unbounded integers, but x + 1 overflows with int32
        source = """
node top(x : int) returns (OK : bool);
let
    OK = x >= 0 => x + 1 > 0;
    --%PROPERTY OK;
    --%MAIN;
tel
"""
        self.assertEqual(EngineResult.REACHABLE, self._translate_and_reach(source, 'int32'))
        self.assertEqual(EngineResult.UNREACHABLE, self._translate_and_reach(source, 'int'))

    def test_unsupported_int_encoding(self):
        with self.assertRaises(Exception):
            translator.translate(from_fixture_path('lustre/peterson_1.lus'), 'top',
                                 'unused.py', 'real', 'int128')

if __name__ == "__main__":
    unittest.main()
