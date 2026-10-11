"""
Tests for intrepyd.diagram: building and simulating circuit diagrams.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from intrepyd import api, diagram
from intrepyd.lib import catalogue

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

    def test_certificates_from_an_intrepid_without_them_are_refused(self):
        with mock.patch.object(api, "HAS_CERTIFICATES", False):
            with self.assertRaisesRegex(diagram.DiagramError, "need intrepid 1.4 or newer"):
                diagram.verify(_counter_to(3), certificates=True)

    def test_the_command_line_verifies_standard_input(self):
        run = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "verify", "-",
                              "--timeout", "30"],
                             input=json.dumps(_counter_to(2)), capture_output=True, text=True,
                             cwd=ROOT, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        [result] = json.loads(run.stdout)["results"]
        self.assertEqual(result["verdict"], "fails")
        self.assertEqual(result["trace"]["steps"], 3)


def _subsystem(nid, name, parent=None):
    node = {"id": nid, "kind": "subsystem", "name": name}
    if parent is not None:
        node["parent"] = parent
    return node


def _inside(node, parent):
    return {**node, "parent": parent}


class SubsystemTest(unittest.TestCase):

    def _xor_of_ands(self):
        """y = (a and b) xor c, the AND inside a sub-system "both" (In a, In b,
        Out ab) and the XOR outside."""
        nodes = [_input(1, "a"), _input(2, "b"), _input(3, "c"), _subsystem(4, "both"),
                 _inside(_input(5, "x"), 4), _inside(_input(6, "y"), 4),
                 _inside(_gate(7, "and"), 4), _inside({"id": 8, "kind": "output", "name": "ab"}, 4),
                 _gate(9, "xor"), {"id": 10, "kind": "output", "name": "out"}]
        edges = [_wire(1, 4, "x"), _wire(2, 4, "y"),
                 _wire(5, 7, "a"), _wire(6, 7, "b"), _wire(7, 8, "in"),
                 _wire(4, 9, "a"), _wire(3, 9, "b"), _wire(9, 10, "in")]
        stimuli = {"1": ["true", "true", "false"], "2": ["true", "false", "true"],
                   "3": ["false", "false", "true"]}
        return _doc(nodes, edges, steps=3, stimuli=stimuli)

    def test_a_subsystem_is_its_blocks(self):
        values = diagram.simulate(self._xor_of_ands())["values"]
        self.assertEqual(values["7.0"], ["T", "F", "F"])  # the AND inside
        self.assertEqual(values["4.0"], ["T", "F", "F"])  # the sub-system's output
        self.assertEqual(values["5.0"], ["T", "T", "F"])  # its In "x" carries a
        self.assertEqual(values["9.0"], ["T", "F", "T"])

    def test_subsystems_nest_and_names_are_prefixed(self):
        # an outer sub-system "outer" holding "both" and a latch, both named
        doc = self._xor_of_ands()
        nodes = doc["circuit"]["nodes"]
        nodes.append(_subsystem(11, "outer"))
        nodes[3]["parent"] = 11  # "both" goes into "outer"
        nodes[6]["name"] = "g"  # its AND
        nodes.extend([_inside(_input(12, "p"), 11), _inside(_input(13, "q"), 11),
                      _inside({"id": 14, "kind": "output", "name": "r"}, 11)])
        doc["circuit"]["edges"] = [e for e in doc["circuit"]["edges"] if e["to"] != 4 and e["from"] != 4]
        doc["circuit"]["edges"] += [_wire(1, 11, "p"), _wire(2, 11, "q"), _wire(12, 4, "x"),
                                    _wire(13, 4, "y"), _wire(4, 14, "in"), _wire(11, 9, "a")]
        values = diagram.simulate(doc)["values"]
        self.assertEqual(values["11.0"], ["T", "F", "F"])
        self.assertEqual(values["9.0"], ["T", "F", "T"])
        circuit = diagram.build(doc)
        self.assertIn("outer.both.g", circuit.ctx.nets)

    def test_a_subsystem_with_a_latch_in_a_loop_through_it(self):
        # a toggle: t' = not t, the latch outside, the NOT inside a sub-system
        nodes = [{"id": 1, "kind": "latch", "name": "t", "type": "bool"},
                 {"id": 2, "kind": "const", "name": None, "op": "false", "value": "false"},
                 _subsystem(3, "inv"), _inside(_input(4, "i"), 3), _inside(_gate(5, "not"), 3),
                 _inside({"id": 6, "kind": "output", "name": "o"}, 3)]
        edges = [_wire(2, 1, "init"), _wire(3, 1, "next"), _wire(1, 3, "i"),
                 _wire(4, 5, "in"), _wire(5, 6, "in")]
        values = diagram.simulate(_doc(nodes, edges, steps=4))["values"]
        self.assertEqual(values["1.0"], ["F", "T", "F", "T"])

    def test_an_unwired_subsystem_input_is_a_readable_error(self):
        doc = self._xor_of_ands()
        doc["circuit"]["edges"] = [e for e in doc["circuit"]["edges"] if e["port"] != "y"]
        with self.assertRaisesRegex(diagram.DiagramError, 'subsystem "both": input "y" is not wired'):
            diagram.simulate(doc)
        doc["circuit"]["edges"].append(_wire(2, 4, "zz"))
        with self.assertRaisesRegex(diagram.DiagramError, 'subsystem "both" has no input "zz"'):
            diagram.simulate(doc)

    def test_a_property_inside_a_subsystem_is_verified(self):
        doc = self._xor_of_ands()
        doc["circuit"]["nodes"].append(_inside({"id": 20, "kind": "assertion", "name": "never_both"}, 4))
        doc["circuit"]["nodes"].append(_inside(_gate(21, "not"), 4))
        doc["circuit"]["edges"] += [_wire(7, 21, "in"), _wire(21, 20, "in")]
        [result] = diagram.verify(doc, timeout=30)["results"]
        self.assertEqual(result["verdict"], "fails")
        self.assertEqual(result["block"], 20)
        stimuli = result["trace"]["stimuli"]
        self.assertEqual((stimuli["1"][-1], stimuli["2"][-1]), ("true", "true"))


class CatalogueTest(unittest.TestCase):

    def test_every_block_builds_with_the_outputs_it_declares(self):
        # each library block, every pin wired from an input of the pin's type
        for spec in catalogue.BLOCKS:
            with self.subTest(spec["symbol"]):
                params = {p["key"]: p["default"] for p in spec["params"]}
                nodes = [{"id": 1, "kind": "component", "name": "b", "module": spec["module"],
                          "symbol": spec["symbol"], "params": params}]
                edges = []
                for k, pin in enumerate(spec["inputs"]):
                    type_ = _type_of(pin["type"], params, spec) or "bool"
                    nodes.append(_input(10 + k, f"i{k}", type_))
                    edges.append(_wire(10 + k, 1, pin["port"]))
                circuit = diagram.build(_doc(nodes, edges))
                self.assertEqual(sorted(i for (b, i) in circuit.outputs if b == 1),
                                 list(range(len(spec["outputs"]))))

    def test_optional_pins_may_stay_unwired(self):
        # a counter to 3 by 1 from 0, then by 2 from 1 when its pins are wired
        def counter(extra_nodes, extra_edges):
            nodes = [{"id": 1, "kind": "component", "name": "k", "module": "eda",
                      "symbol": "mk_counter", "params": {"t": "int8"}},
                     {"id": 2, "kind": "const", "name": None, "type": "int8", "value": "5"}] + extra_nodes
            edges = [_wire(2, 1, "limit")] + extra_edges
            return diagram.simulate(_doc(nodes, edges, steps=4))["values"]["1.0"]
        self.assertEqual(counter([], []), ["0", "1", "2", "3"])
        ones = [{"id": 3, "kind": "const", "name": None, "type": "int8", "value": "1"},
                {"id": 4, "kind": "const", "name": None, "type": "int8", "value": "2"}]
        self.assertEqual(counter(ones, [_wire(3, 1, "init"), _wire(4, 1, "increment")]),
                         ["1", "3", "5", "5"])

    def test_the_command_line_prints_the_catalogue(self):
        run = subprocess.run([sys.executable, "-m", "intrepyd.diagram", "catalogue"],
                             capture_output=True, text=True, cwd=ROOT, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["format"], catalogue.FORMAT)
        self.assertEqual([b["symbol"] for b in data["blocks"]], [b["symbol"] for b in catalogue.BLOCKS])


def _type_of(ref, params, spec):
    if ref is None:
        return None
    if ref["kind"] == "bool":
        return "bool"
    if ref["kind"] == "param":
        return params[ref["key"]]
    other = next(p for p in spec["inputs"] if p["port"] == ref["port"])
    return _type_of(other["type"], params, spec)


if __name__ == "__main__":
    unittest.main()
