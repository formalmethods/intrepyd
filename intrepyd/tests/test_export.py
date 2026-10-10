"""
Tests for intrepyd.export, the JSON netlist exporter.

They build a fake Context (just the recipe, net2name and outputs that the
exporter reads), so they need neither the native library nor a real circuit:
the exporter is pure python over the recipe. The module is loaded directly from
its file so importing it does not pull in the whole package (which needs the
library).
"""

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPORT_PY = os.path.join(_HERE, os.pardir, "export.py")


def _load_export():
    try:
        from intrepyd import export  # noqa: available when the library is installed
        return export
    except Exception:  # pylint: disable=broad-except
        spec = importlib.util.spec_from_file_location("intrepyd_export", _EXPORT_PY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


export = _load_export()


class _Recipe:
    def __init__(self, calls, refs, locations=None):
        self.calls = calls
        self._refs = refs
        self.locations = locations or []


class _FakeContext:
    """The attributes intrepyd.export reads off a real Context."""

    # distinct ints for the type nets and the predefined nets
    _TYPES = ("booleantype", "int8type", "int16type", "int32type", "int64type",
              "uint8type", "uint16type", "uint32type", "uint64type", "realtype",
              "float16type", "float32type", "float64type", "inttype")

    def __init__(self, calls, refs, net2name, outputs, locations=None):
        for i, attr in enumerate(self._TYPES):
            setattr(self, attr, 10 + i)
        self.true, self.false, self.undef = 1, 2, 3
        self.recipe = _Recipe(calls, refs, locations)
        self.net2name = net2name
        self.outputs = outputs


def _and_counter_context():
    """input a & b -> output, plus a latch counter = 0 -> counter + 1."""
    calls = [
        ("mk_input", (("value", "a"), ("attr", "booleantype")), {}),           # 0 -> 101
        ("mk_input", (("value", "b"), ("attr", "booleantype")), {}),           # 1 -> 102
        ("mk_and", (("net", 0), ("net", 1)), {}),                              # 2 -> 103
        ("mk_output", (("net", 2),), {}),                                      # 3 -> None
        ("mk_latch", (("value", "counter"), ("attr", "int8type")), {}),        # 4 -> 201
        ("mk_number", (("value", "0"), ("attr", "int8type")), {}),             # 5 -> 202
        ("mk_number", (("value", "1"), ("attr", "int8type")), {}),             # 6 -> 203
        ("mk_add", (("net", 4), ("net", 6)), {}),                              # 7 -> 204
        ("set_latch_init_next", (("net", 4), ("net", 5), ("net", 7)), {}),     # 8 -> None
    ]
    refs = {101: ("net", 0), 102: ("net", 1), 103: ("net", 2),
            201: ("net", 4), 202: ("net", 5), 203: ("net", 6), 204: ("net", 7),
            1: ("attr", "true"), 2: ("attr", "false"), 3: ("attr", "undef")}
    net2name = {101: "a", 102: "b", 103: "__n103",
                201: "counter", 202: "__n202", 203: "__n203", 204: "__n204"}
    outputs = {"__o103": 103}
    return _FakeContext(calls, refs, net2name, outputs)


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.graph = export.to_graph(_and_counter_context())
        self.nodes = {n["id"]: n for n in self.graph["nodes"]}
        self.edges = self.graph["edges"]

    def test_version_and_node_set(self):
        self.assertEqual(self.graph["version"], 2)
        self.assertEqual(set(self.nodes), {101, 102, 103, 201, 202, 203, 204})

    def test_no_source_location_without_recipe_locations(self):
        # the and-counter context records no locations: no file/line on any node
        for node in self.nodes.values():
            self.assertNotIn("file", node)
            self.assertNotIn("line", node)

    def test_inputs(self):
        self.assertEqual(self.nodes[101]["kind"], "input")
        self.assertEqual(self.nodes[101]["name"], "a")
        self.assertEqual(self.nodes[101]["type"], "bool")

    def test_gate_and_made_up_name_is_null(self):
        self.assertEqual(self.nodes[103]["kind"], "gate")
        self.assertEqual(self.nodes[103]["op"], "and")
        self.assertIsNone(self.nodes[103]["name"])  # __n103 is intrepyd's own name

    def test_output_is_a_flag_on_its_net(self):
        self.assertTrue(self.nodes[103].get("output"))
        # and nothing else is an output
        self.assertFalse(any(n.get("output") for i, n in self.nodes.items() if i != 103))

    def test_latch_and_constants(self):
        self.assertEqual(self.nodes[201]["kind"], "latch")
        self.assertEqual(self.nodes[201]["type"], "int8")
        self.assertEqual(self.nodes[202]["kind"], "const")
        self.assertEqual(self.nodes[202]["value"], "0")
        self.assertEqual(self.nodes[203]["value"], "1")

    def test_edges_of_the_and(self):
        into_and = {(e["from"], e["port"]) for e in self.edges if e["to"] == 103}
        self.assertEqual(into_and, {(101, "a"), (102, "b")})

    def test_latch_init_and_next_ports(self):
        into_latch = {(e["from"], e["port"]) for e in self.edges if e["to"] == 201}
        self.assertEqual(into_latch, {(202, "init"), (204, "next")})

    def test_add_feeds_from_counter_and_one(self):
        into_add = {(e["from"], e["port"]) for e in self.edges if e["to"] == 204}
        self.assertEqual(into_add, {(201, "a"), (203, "b")})

    def test_ite_ports(self):
        # i ? t : e  with i=true, t=number, e=number
        calls = [
            ("mk_true", (), {}),                                   # 0 -> 1 (predefined)
            ("mk_number", (("value", "7"), ("attr", "int8type")), {}),  # 1 -> 301
            ("mk_number", (("value", "9"), ("attr", "int8type")), {}),  # 2 -> 302
            ("mk_ite", (("attr", "true"), ("net", 1), ("net", 2)), {}),  # 3 -> 303
        ]
        refs = {1: ("net", 0), 301: ("net", 1), 302: ("net", 2), 303: ("net", 3),
                2: ("attr", "false"), 3: ("attr", "undef")}
        ctx = _FakeContext(calls, refs, {301: "__n301", 302: "__n302", 303: "r"}, {})
        graph = export.to_graph(ctx)
        edges = {(e["from"], e["port"]) for e in graph["edges"] if e["to"] == 303}
        self.assertEqual(edges, {(1, "if"), (301, "then"), (302, "else")})
        # the predefined true became a const node so the graph stays connected
        true_node = next(n for n in graph["nodes"] if n["id"] == 1)
        self.assertEqual(true_node["kind"], "const")
        self.assertEqual(true_node["value"], "true")

    def test_namespace_becomes_group(self):
        calls = [("mk_input", (("value", "Counter.q"), ("attr", "booleantype")), {})]
        refs = {101: ("net", 0)}
        ctx = _FakeContext(calls, refs, {101: "Counter.q"}, {})
        node = export.to_graph(ctx)["nodes"][0]
        self.assertEqual(node["name"], "Counter.q")
        self.assertEqual(node["group"], "Counter")

    def test_source_location_is_carried_to_the_node(self):
        # recipe.locations is aligned with recipe.calls by index; the net each
        # call produced takes its (file, line).
        calls = [
            ("mk_input", (("value", "a"), ("attr", "booleantype")), {}),  # 0 -> 101
            ("mk_input", (("value", "b"), ("attr", "booleantype")), {}),  # 1 -> 102
            ("mk_and", (("net", 0), ("net", 1)), {}),                     # 2 -> 103
        ]
        refs = {101: ("net", 0), 102: ("net", 1), 103: ("net", 2)}
        locations = [("/p/prog.py", 5), ("/p/prog.py", 6), ("/p/prog.py", 7)]
        ctx = _FakeContext(calls, refs, {101: "a", 102: "b", 103: "__n"}, {}, locations)
        nodes = {n["id"]: n for n in export.to_graph(ctx)["nodes"]}
        self.assertEqual((nodes[101]["file"], nodes[101]["line"]), ("/p/prog.py", 5))
        self.assertEqual((nodes[103]["file"], nodes[103]["line"]), ("/p/prog.py", 7))

    def test_missing_location_is_omitted(self):
        # a None in locations (intrepyd could not find the caller) -> no file/line
        calls = [("mk_input", (("value", "a"), ("attr", "booleantype")), {})]
        refs = {101: ("net", 0)}
        ctx = _FakeContext(calls, refs, {101: "a"}, {}, locations=[None])
        node = export.to_graph(ctx)["nodes"][0]
        self.assertNotIn("file", node)
        self.assertNotIn("line", node)


class _FakeTrace:
    """What intrepyd.export reads off a Trace."""

    def __init__(self, ctx, depth, netvals):
        self.ctx = ctx
        self._depth = depth
        self._netvals = netvals

    def get_max_depth(self):
        return self._depth

    def get_as_net_dictionary(self):
        return self._netvals


class TraceExportTest(unittest.TestCase):
    def test_trace_payload_shapes_the_watched_nets(self):
        trace = _FakeTrace(ctx=5, depth=3, netvals={101: ["T", "F"], 102: ["0", "1"]})
        payload = export.trace_payload(trace)
        self.assertEqual(payload["depth"], 3)
        self.assertEqual(payload["values"], {"101": ["T", "F"], "102": ["0", "1"]})

    def test_trace_for_picks_the_matching_context_with_values(self):
        class _Ctx:
            ctx = 7

        context = _Ctx()
        empty = _FakeTrace(ctx=7, depth=0, netvals={})  # no depth
        other = _FakeTrace(ctx=9, depth=2, netvals={1: ["T"]})  # wrong context
        good = _FakeTrace(ctx=7, depth=2, netvals={1: ["T", "F"]})
        self.assertIs(export._trace_for(context, [empty, other, good]), good)
        self.assertIsNone(export._trace_for(context, [empty, other]))


if __name__ == "__main__":
    unittest.main()
