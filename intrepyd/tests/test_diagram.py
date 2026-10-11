"""
Tests for intrepyd.diagram: building and simulating circuit diagrams.
"""

import json
import os
import subprocess
import sys
import unittest

from intrepyd import diagram

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)


def _doc(nodes, edges, steps=None, stimuli=None):
    doc = {"format": diagram.FORMAT, "version": diagram.VERSION,
           "circuit": {"nodes": nodes, "edges": edges}, "layout": {"blocks": {}}}
    if steps is not None:
        doc["simulation"] = {"steps": steps, "stimuli": stimuli or {}}
    return doc


def _input(nid, name, type_="bool"):
    return {"id": nid, "kind": "input", "name": name, "type": type_}


def _wire(src, dst, port, from_port=None):
    edge = {"from": src, "to": dst, "port": port}
    if from_port is not None:
        edge["fromPort"] = from_port
    return edge


class DiagramTest(unittest.TestCase):

    def test_and_simulated_step_by_step(self):
        doc = _doc([_input(1, "a"), _input(2, "b"), {"id": 3, "kind": "gate", "name": None, "op": "and"},
                    {"id": 4, "kind": "output", "name": "y"}],
                   [_wire(1, 3, "a"), _wire(2, 3, "b"), _wire(3, 4, "in")],
                   steps=4, stimuli={"1": ["true", "true", "false", "false"],
                                     "2": ["true", "false", "true", "false"]})
        result = diagram.simulate(doc)
        self.assertEqual(result["steps"], 4)
        self.assertEqual(result["values"]["3.0"], ["T", "F", "F", "F"])
        self.assertEqual(result["values"]["1.0"], ["T", "T", "F", "F"])

    def test_a_counting_latch(self):
        # c = 0 at step 0, then c + 1
        doc = _doc([{"id": 1, "kind": "latch", "name": "c", "type": "int8"},
                    {"id": 2, "kind": "const", "name": None, "type": "int8", "value": "0"},
                    {"id": 3, "kind": "const", "name": None, "type": "int8", "value": "1"},
                    {"id": 4, "kind": "gate", "name": None, "op": "add"},
                    {"id": 5, "kind": "output", "name": "count"}],
                   [_wire(2, 1, "init"), _wire(4, 1, "next"), _wire(1, 4, "a"), _wire(3, 4, "b"),
                    _wire(1, 5, "in")], steps=5)
        self.assertEqual(diagram.simulate(doc)["values"]["1.0"], ["0", "1", "2", "3", "4"])

    def test_a_three_input_and_is_a_chain(self):
        nodes = [_input(1, "a"), _input(2, "b"), _input(3, "c"),
                 {"id": 4, "kind": "gate", "name": "all3", "op": "and", "inputs": 3}]
        edges = [_wire(1, 4, "in0"), _wire(2, 4, "in1"), _wire(3, 4, "in2")]
        stimuli = {"1": ["true", "true"], "2": ["true", "true"], "3": ["true", "false"]}
        result = diagram.simulate(_doc(nodes, edges, steps=2, stimuli=stimuli))
        self.assertEqual(result["values"]["4.0"], ["T", "F"])

    def test_a_switch_and_a_comparison(self):
        nodes = [_input(1, "x", "int8"), _input(2, "y", "int8"),
                 {"id": 3, "kind": "gate", "name": None, "op": "gt"},
                 {"id": 4, "kind": "gate", "name": "max", "op": "ite"}]
        edges = [_wire(1, 3, "a"), _wire(2, 3, "b"),
                 _wire(3, 4, "if"), _wire(1, 4, "then"), _wire(2, 4, "else")]
        stimuli = {"1": ["3", "-2"], "2": ["1", "5"]}
        self.assertEqual(diagram.simulate(_doc(nodes, edges, steps=2, stimuli=stimuli))["values"]["4.0"],
                         ["3", "5"])

    def test_a_library_block_and_its_outputs(self):
        # a TON with a preset of 2: Q rises two steps after its input does
        nodes = [_input(1, "go"), {"id": 2, "kind": "const", "name": None, "type": "int8", "value": "2"},
                 {"id": 3, "kind": "component", "name": "t", "module": "plc", "symbol": "mk_ton",
                  "params": {"typ": "int8"}},
                 {"id": 4, "kind": "output", "name": "done"}]
        edges = [_wire(1, 3, "in"), _wire(2, 3, "pt"), _wire(3, 4, "in", from_port=1)]
        result = diagram.simulate(_doc(nodes, edges, steps=5, stimuli={"1": ["true"] * 5}))
        values = result["values"]
        self.assertIn("3.0", values)  # ET
        self.assertIn("3.1", values)  # Q
        self.assertEqual(values["3.1"][0], "F")
        self.assertEqual(values["3.1"][-1], "T")

    def test_an_unwired_input_is_a_readable_error(self):
        doc = _doc([_input(1, "a"), {"id": 2, "kind": "gate", "name": None, "op": "and"}],
                   [_wire(1, 2, "a")], steps=2)
        with self.assertRaisesRegex(diagram.DiagramError, 'and 2: input "b" is not wired'):
            diagram.simulate(doc)

    def test_not_a_diagram(self):
        with self.assertRaisesRegex(diagram.DiagramError, "not an intrepyd diagram"):
            diagram.load({"version": 3})
        with self.assertRaisesRegex(diagram.DiagramError, "unsupported diagram version"):
            diagram.load({"format": diagram.FORMAT, "version": 2})

    def test_the_command_line_reads_standard_input(self):
        doc = _doc([_input(1, "a"), {"id": 2, "kind": "gate", "name": None, "op": "not"}],
                   [_wire(1, 2, "in")], steps=3, stimuli={"1": ["true", "false", "true"]})
        run = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "simulate", "-"],
                             input=json.dumps(doc), capture_output=True, text=True, cwd=ROOT,
                             check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["values"]["2.0"], ["F", "T", "F"])
        # and a broken one says why, on standard error
        bad = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "simulate", "-"],
                             input='{"format": "x"}', capture_output=True, text=True, cwd=ROOT,
                             check=False)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("not an intrepyd diagram", bad.stderr)



def _gate(nid, op, name=None):
    return {"id": nid, "kind": "gate", "name": name, "op": op}


def _counter_to(limit):
    """c = 0, c + 1, ... and an assertion that c never equals `limit`."""
    nodes = [{"id": 1, "kind": "latch", "name": "c", "type": "int8"},
             {"id": 2, "kind": "const", "name": None, "type": "int8", "value": "0"},
             {"id": 3, "kind": "const", "name": None, "type": "int8", "value": "1"},
             _gate(4, "add"),
             {"id": 5, "kind": "const", "name": None, "type": "int8", "value": str(limit)},
             _gate(6, "neq"),
             {"id": 7, "kind": "assertion", "name": "never_limit"}]
    edges = [_wire(2, 1, "init"), _wire(4, 1, "next"), _wire(1, 4, "a"), _wire(3, 4, "b"),
             _wire(1, 6, "a"), _wire(5, 6, "b"), _wire(6, 7, "in")]
    return _doc(nodes, edges)


class VerifyTest(unittest.TestCase):

    def test_an_assertion_that_always_holds(self):
        doc = _doc([_input(1, "a"), _gate(2, "not"), _gate(3, "and"), _gate(4, "not"),
                    {"id": 5, "kind": "assertion", "name": "consistent"}],
                   [_wire(1, 2, "in"), _wire(1, 3, "a"), _wire(2, 3, "b"), _wire(3, 4, "in"),
                    _wire(4, 5, "in")])
        [result] = diagram.verify(doc, timeout=30)["results"]
        self.assertEqual(result["verdict"], "holds")
        self.assertEqual(result["name"], "consistent")
        self.assertNotIn("trace", result)

    def test_a_failing_assertion_comes_with_its_counterexample(self):
        [result] = diagram.verify(_counter_to(3), timeout=30)["results"]
        self.assertEqual(result["verdict"], "fails")
        trace = result["trace"]
        self.assertEqual(trace["steps"], 4)  # c is 3 at step 3
        self.assertEqual(trace["values"]["1.0"], ["0", "1", "2", "3"])
        self.assertEqual(trace["values"]["6.0"][-1], "F")  # where the assertion fails

    def test_a_target_reached_and_one_unreachable(self):
        doc = _doc([_input(1, "a"), _input(2, "b"), _gate(3, "and"),
                    {"id": 4, "kind": "target", "name": "both"},
                    {"id": 5, "kind": "latch", "name": "stuck", "type": "bool"},
                    {"id": 6, "kind": "const", "name": None, "op": "false", "value": "false"},
                    {"id": 7, "kind": "target", "name": "never"}],
                   [_wire(1, 3, "a"), _wire(2, 3, "b"), _wire(3, 4, "in"),
                    _wire(6, 5, "init"), _wire(5, 5, "next"), _wire(5, 7, "in")])
        results = {r["name"]: r for r in diagram.verify(doc, timeout=30)["results"]}
        self.assertEqual(results["both"]["verdict"], "reached")
        stimuli = results["both"]["trace"]["stimuli"]
        self.assertEqual((stimuli["1"][-1], stimuli["2"][-1]), ("true", "true"))
        self.assertEqual(results["never"]["verdict"], "unreachable")
        self.assertIsNotNone(results["never"]["engine"])

    def test_bounded_model_checking_cannot_prove(self):
        [result] = diagram.verify(_counter_to(-1), engine="bmc", depth=5, timeout=10)["results"]
        self.assertEqual(result["verdict"], "unknown")

    def test_nothing_to_verify_and_an_unknown_engine(self):
        doc = _doc([_input(1, "a")], [])
        with self.assertRaisesRegex(diagram.DiagramError, "no assertion and no target"):
            diagram.verify(doc)
        with self.assertRaisesRegex(diagram.DiagramError, 'unknown engine "z3"'):
            diagram.verify(_counter_to(3), engine="z3")

    def test_the_command_line_verifies_standard_input(self):
        run = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "verify", "-",
                              "--timeout", "30"],
                             input=json.dumps(_counter_to(2)), capture_output=True, text=True,
                             cwd=ROOT, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        [result] = json.loads(run.stdout)["results"]
        self.assertEqual(result["verdict"], "fails")
        self.assertEqual(result["trace"]["steps"], 3)


if __name__ == "__main__":
    unittest.main()
