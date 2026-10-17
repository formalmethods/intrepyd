"""
A Lustre model opened as a circuit (intrepyd.export on a .lus file): what the
file is (describe), what is refused and where (a syntax error, a construct
not supported, Kind2's contracts), its properties as assertions and its
assertions as assumptions in the graph, and an assumption block of a diagram
kept to by the engines. The models here are made up.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from intrepyd import diagram, export
from intrepyd.lustre2py import translator
from intrepyd.lustre2py.errors import LustreError

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)

COUNTER = """
-- a counter that saturates, with an assumption on its input (made up)
node sat(x: int) returns (y: int);
let
  y = if x > 10 then 10 else x;
  --%PROPERTY y <= 10;
tel

node top(inc: bool; step: int) returns (count: int; OK: bool);
var raw: int;
let
  assert step >= 0 and step <= 3;
  raw = 0 -> pre count + (if inc then step else 0);
  count = sat(raw);
  OK = count >= 0;
  --%PROPERTY OK;
  --%PROPERTY count < 10;
tel
"""


class LustreImportTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.tmp.cleanup)

    def lus(self, text, name='model.lus'):
        path = os.path.join(self.tmp.name, name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return path

    def refused(self, text, message, line=None):
        with self.assertRaises(LustreError) as caught:
            translator.describe(self.lus(text))
        self.assertIn(message, caught.exception.message)
        if line is not None:
            self.assertEqual(caught.exception.line, line)

    def test_what_the_file_is(self):
        about = translator.describe(self.lus(COUNTER))
        self.assertEqual(about, {'nodes': ['sat', 'top'], 'main': None, 'candidates': ['top'], 'int': True,
                                 'real': False, 'properties': 3, 'assertions': 1})
        about = translator.describe(self.lus('node a(x: real) returns (y: bool);\nlet y = x > 0.5; --%MAIN;\ntel\n'
                                             'node b(z: bool) returns (w: bool);\nlet w = z; tel\n'))
        self.assertEqual((about['main'], about['candidates'], about['int'], about['real']), ('a', ['a', 'b'], False, True))

    def test_what_is_refused_and_where(self):
        self.refused('node top(x: bool) returns (y: bool);\nlet\n  y = x and ;\ntel\n', 'syntax error', 3)
        self.refused('node top(x: int[3]) returns (y: bool);\nlet y = true; tel\n', 'arrays are not supported', 1)
        self.refused('const N = 3;\nnode top(x: bool) returns (y: bool);\nlet y = x; tel\n',
                     'constants are not supported', 1)
        self.refused('node top(x: bool) returns (y: bool);\n(*@contract guarantee y; *)\nlet y = x; tel\n',
                     "Kind2's contracts are not supported", 2)
        self.refused('node top(x: bool) returns (y: bool);\n--@ensure y;\nlet y = x; tel\n',
                     "Kind2's contracts are not supported", 2)
        self.refused('node top(x: real) returns (y: int);\nlet y = floor(x); tel\n', 'casts', 2)
        path = self.lus('node a(x: bool) returns (y: bool);\nlet y = x; tel\nnode b(x: bool) returns (y: bool);\n'
                        'let y = not x; tel\n')
        with self.assertRaisesRegex(LustreError, r'several top nodes \(a, b\)'):
            export.lustre_graph(path)
        with self.assertRaisesRegex(LustreError, 'no node c'):
            export.lustre_graph(path, node='c')
        self.assertIn('input', [n['kind'] for n in export.lustre_graph(path, node='b')['nodes']])

    def test_the_encodings_are_asked_not_chosen(self):
        path = self.lus(COUNTER)
        with self.assertRaisesRegex(LustreError, 'the model uses int: give its encoding'):
            export.lustre_graph(path)
        types = {n.get('type') for n in export.lustre_graph(path, int_type='int8')['nodes']}
        self.assertIn('int8', types)

    def test_properties_as_assertions_assertions_as_assumptions(self):
        graph = export.lustre_graph(self.lus(COUNTER), int_type='int')
        self.assertEqual(graph['version'], 3)
        checks = {n['name']: n['kind'] for n in graph['nodes'] if n['kind'] in ('assertion', 'assumption')}
        self.assertEqual(checks, {'sat.property_line6': 'assertion', 'OK': 'assertion',
                                  'property_line17': 'assertion', 'assumption_line12': 'assumption'})
        for node in graph['nodes']:
            if node['kind'] in ('assertion', 'assumption'):
                self.assertEqual(len([e for e in graph['edges'] if e['to'] == node['id'] and e['port'] == 'in']), 1)
        scoped = {n.get('op') for n in graph['nodes'] if n.get('scope') == 'sat.1'}
        self.assertIn('gt', scoped, "the gates of sat's instance carry its scope, named or not")
        self.assertFalse([n for n in graph['nodes'] if (n['name'] or '').endswith('__n')], 'no made-up names')
        outputs = {n['name'] for n in graph['nodes'] if n.get('output')}
        self.assertEqual(outputs, {'count', 'OK'}, 'every output of the top node, not the first twice')

    def test_the_command_line(self):
        path = self.lus(COUNTER)
        run = subprocess.run([sys.executable, '-m', 'intrepyd.export', path, '--describe'], capture_output=True,
                             text=True, cwd=ROOT, check=False)
        self.assertEqual(json.loads(run.stdout)['candidates'], ['top'], run.stderr)
        run = subprocess.run([sys.executable, '-m', 'intrepyd.export', path], capture_output=True, text=True,
                             cwd=ROOT, check=False)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{path}: the model uses int', run.stderr)
        bad = self.lus('node top(x: bool) returns (y: bool);\nlet\n  y = x and ;\ntel\n', 'bad.lus')
        run = subprocess.run([sys.executable, '-m', 'intrepyd.export', bad], capture_output=True, text=True,
                             cwd=ROOT, check=False)
        self.assertRegex(run.stderr.strip(), r'bad\.lus:3:\d+: syntax error')
        run = subprocess.run([sys.executable, '-m', 'intrepyd.export', path, '--int', 'int32'], capture_output=True,
                             text=True, cwd=ROOT, check=False)
        self.assertEqual(json.loads(run.stdout)['version'], 3, run.stderr)


def _doc(nodes, edges):
    return {"format": diagram.FORMAT, "version": diagram.VERSION, "circuit": {"nodes": nodes, "edges": edges},
            "layout": {"blocks": {}}}


class AssumptionBlockTest(unittest.TestCase):
    """x an int8 input; "small" asserts x <= 5, which holds only where x <= 3 is assumed."""

    def doc(self, assumed):
        nodes = [{"id": 1, "kind": "input", "name": "x", "type": "int8"},
                 {"id": 2, "kind": "const", "name": None, "type": "int8", "value": "5"},
                 {"id": 3, "kind": "gate", "name": None, "op": "leq"},
                 {"id": 4, "kind": "assertion", "name": "small"}]
        edges = [{"from": 1, "to": 3, "port": "a"}, {"from": 2, "to": 3, "port": "b"},
                 {"from": 3, "to": 4, "port": "in"}]
        if assumed:
            nodes += [{"id": 5, "kind": "const", "name": None, "type": "int8", "value": "3"},
                      {"id": 6, "kind": "gate", "name": None, "op": "leq"},
                      {"id": 7, "kind": "assumption", "name": "x_at_most_3"}]
            edges += [{"from": 1, "to": 6, "port": "a"}, {"from": 5, "to": 6, "port": "b"},
                      {"from": 6, "to": 7, "port": "in"}]
        return _doc(nodes, edges)

    def test_the_engines_keep_to_the_assumption(self):
        [free] = diagram.verify(self.doc(False), timeout=30)["results"]
        self.assertEqual(free["verdict"], "fails")
        results = diagram.verify(self.doc(True), timeout=30)["results"]
        self.assertEqual([(r["name"], r["verdict"]) for r in results], [("small", "holds")],
                         "the assumption is not a property to check")
        for engine in ("bmc", "kind", "br", "pdr"):
            [one] = diagram.verify(self.doc(True), engine=engine, timeout=30, depth=10)["results"]
            self.assertIn(one["verdict"], ("holds", "unknown"), engine)
            self.assertNotEqual(one["verdict"], "fails", engine)

    def test_a_lustre_assertion_constrains_its_properties(self):
        """The made-up counter: count < 10 fails (step reaches 3 at most, but count
        still climbs to 10), and with step <= 3 assumed y <= 10 holds."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'counter.lus')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(COUNTER)
            graph = export.lustre_graph(path, int_type='int')
        nodes = [dict(n, id=n['id']) for n in graph['nodes'] if n['kind'] != 'external']
        verdicts = {r["name"]: r["verdict"]
                    for r in diagram.verify(_doc(nodes, graph['edges']), timeout=60)["results"]}
        self.assertEqual(verdicts, {'sat.property_line6': 'holds', 'OK': 'holds', 'property_line17': 'fails'})


if __name__ == '__main__':
    unittest.main()
