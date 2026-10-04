"""
Tests of the ctypes binding in intrepyd.api, rather than of intrepyd itself
"""

import os
import re
import tempfile
import unittest

from intrepyd import api

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def _find_header():
    path = os.environ.get('INTREPID_HEADER', os.path.join(ROOT, '.intrepid', 'Intrepid.h'))
    return path if os.path.isfile(path) else None


def _parse_header(path):
    """Returns {name: (result type, argument types)} for Intrepid.h"""
    types = {
        'Int_ctx': api.HANDLE, 'Int_type': api.HANDLE, 'Int_engine_bmc': api.HANDLE,
        'Int_engine_br': api.HANDLE, 'Int_engine_ti': api.HANDLE,
        'Int_engine_pdr': api.HANDLE,
        'Int_simulator': api.HANDLE, 'Int_trace': api.HANDLE,
        'Int_net': api.UINT, 'unsigned': api.UINT, 'Int_engine_result': api.INT,
        'const char*': api.STR, 'char*': api.STR, 'char': api.CHAR, 'void': api.VOID,
    }

    def ctype(declaration):
        declaration = ' '.join(declaration.split())
        match = re.match(r'^(const )?(\w+) ?(\*?) ?\w*$', declaration)
        const, base, star = match.groups()
        return types[(const or '') + base + star]

    with open(path) as header:
        text = re.sub(r'/\*.*?\*/', '', header.read(), flags=re.S)
    text = text[text.index('extern "C"'):]
    functions = {}
    for match in re.finditer(r'DLLEXPORT\s+([^;(]*?)\b(\w+)\s*\(([^)]*)\)\s*;', text):
        result, name, params = match.groups()
        params = params.strip()
        args = () if params in ('', 'void') else \
            tuple(ctype(param) for param in params.split(','))
        functions[name] = (ctype(result), args)
    return functions


class TestApi(unittest.TestCase):

    def test_every_function_is_in_the_library(self):
        missing = [name for name in api.FUNCTIONS if not hasattr(api._lib, name)]
        self.assertEqual(missing, [])

    @unittest.skipIf(_find_header() is None,
                     'no Intrepid.h: run fetch_intrepid.py, or set INTREPID_HEADER')
    def test_functions_match_the_header(self):
        self.assertEqual(api.FUNCTIONS, _parse_header(_find_header()))

    def test_strings_and_handles(self):
        ctx = api.mk_ctx()
        self.assertIsNotNone(ctx)
        int8 = api.mk_int8_type(ctx)
        net = api.mk_number(ctx, '-12', int8)
        self.assertIsInstance(net, int)
        length = api.prepare_value_for_net(ctx, net)
        value = ''.join(api.value_at(i) for i in range(length))
        # At this level an int8 is a bitvector, and 0xf4 is -12
        self.assertEqual(value, '#xf4')
        api.del_ctx(ctx)

    def test_errors_raise_and_are_cleared(self):
        # On an error the library writes the API trace to trace.cpp in the
        # current directory, so keep it out of the source tree
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with self.assertRaisesRegex(RuntimeError, 'NULL context'):
                    api.mk_engine_bmc(None)
                self.assertIsNone(api.check_exception())
                # The next call is not affected by the previous error
                ctx = api.mk_ctx()
                self.assertIsNotNone(api.mk_engine_bmc(ctx))
                api.del_ctx(ctx)
            finally:
                os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
