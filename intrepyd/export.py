"""
Exports the circuit of a Context as a JSON graph (a netlist), so that it can be
drawn as a block diagram — the intrepid-vscode extension (roadmap #28 of
intrepid-specs) is the first consumer, but the format is generic.

The structure comes from the context's *recipe* (``intrepyd.recipe``), the
record of the calls that built every net, which already holds each net's
operator and its fanin as references; names come from ``net2name`` and the
outputs from ``context.outputs``. Nothing is read from the native library, so
the export is pure python and works wherever a built ``Context`` does.

JSON schema (``version`` 1)
---------------------------

::

    {
      "version": 1,
      "nodes": [
        {
          "id":    <int>,         # the net, unique in the graph; edges use it
          "kind":  "input" | "latch" | "const" | "gate" | "output" | "external",
          "name":  <str|null>,    # the user's name, null if intrepyd made one up
          "op":    <str|null>,    # for a gate: "and", "add", "ite", ...; for a
                                  #   boolean constant: "true"/"false"; else absent
          "type":  <str|null>,    # "bool", "int8", ..., "int", "real", "float32"
                                  #   when known (input/latch/const), else absent
          "value": <str>,         # for a const: "0", "true", "?", ... (else absent)
          "group": <str>,         # the namespace of the name, e.g. "Counter" for
                                  #   "Counter.q" (else absent)
          "output": true          # present only when the net is tagged an output
        }
      ],
      "edges": [
        { "from": <int>, "to": <int>, "port": <str> }
        # the net <from> feeds input port <port> of net <to>; ports are
        # "init"/"next" for a latch, "if"/"then"/"else" for an ite, "in" for a
        # unary operator, "a"/"b" for a binary one, else "in0", "in1", ...
      ]
    }

A node is one net. Outputs are a flag on the net they tag, not separate nodes.
``const`` covers numbers and the predefined ``true``/``false``/``undef`` (whose
value is ``"?"``). A fanin that was built outside the context appears as an
``external`` node with no detail, so the graph stays connected.
"""

import argparse
import json
import runpy
import sys

# A Context's type attribute -> the readable type name used in the graph. Kept
# here (not imported) so this module loads without the native library; update it
# if intrepyd gains a type.
_TYPE_ATTR_TO_NAME = {
    "booleantype": "bool",
    "int8type": "int8", "int16type": "int16", "int32type": "int32", "int64type": "int64",
    "uint8type": "uint8", "uint16type": "uint16", "uint32type": "uint32", "uint64type": "uint64",
    "realtype": "real",
    "float16type": "float16", "float32type": "float32", "float64type": "float64",
    "inttype": "int",
}

# The predefined nets of a Context, usable as a fanin.
_PREDEFINED = ("true", "false", "undef")

# Method name -> its input port names; a gate not listed here uses "a"/"b" for
# two inputs, or "in0", "in1", ... otherwise.
_PORTS = {
    "mk_not": ["in"],
    "mk_minus": ["in"],
    "mk_ite": ["if", "then", "else"],
}
for _cast in ("int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"):
    _PORTS["mk_cast_to_" + _cast] = ["in"]


def to_graph(context):
    """The circuit of ``context`` as a JSON-able dict following the schema above."""
    recipe = context.recipe
    # Each call that returned a net is recorded in the recipe as ('net', idx);
    # invert that to map a call index back to the net it produced.
    refs = recipe._refs  # pylint: disable=protected-access
    idx2net = {ref[1]: net for net, ref in refs.items() if ref[0] == "net"}

    attr_nets = {attr: getattr(context, attr) for attr in _PREDEFINED if hasattr(context, attr)}
    predefined = {net: attr for attr, net in attr_nets.items()}
    net2name = dict(getattr(context, "net2name", {}))
    output_nets = set(getattr(context, "outputs", {}).values())

    return _build(recipe.calls, idx2net, attr_nets, predefined, net2name, output_nets)


def to_json(context, indent=2):
    """The circuit of ``context`` as a JSON string."""
    return json.dumps(to_graph(context), indent=indent)


def dump(context, path, indent=2):
    """Writes the circuit of ``context`` as JSON to ``path``."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_json(context, indent=indent))
        handle.write("\n")


def _build(calls, idx2net, attr_nets, predefined, net2name, output_nets):
    # pylint: disable=too-many-locals,too-many-statements  # one pass with a few local helpers
    nodes = {}
    edges = []

    def node(net, kind, op=None, type_=None, value=None):
        name = net2name.get(net)
        if name is not None and name.startswith("__"):  # intrepyd's made-up name
            name = None
        entry = {"id": net, "kind": kind, "name": name}
        if op is not None:
            entry["op"] = op
        if type_ is not None:
            entry["type"] = type_
        if value is not None:
            entry["value"] = value
        if name is not None and "." in name:
            entry["group"] = name.rsplit(".", 1)[0]
        nodes[net] = entry
        return entry

    def ensure(net):
        """A node must exist for every net that an edge touches."""
        if net in nodes:
            return
        if net in predefined:
            name = predefined[net]
            node(net, "const", op=None if name == "undef" else name,
                 value="?" if name == "undef" else name)
        else:
            node(net, "external")

    def as_net(ref):
        kind, value = ref
        if kind == "net":
            return idx2net.get(value)
        if kind == "attr":
            return attr_nets.get(value)  # true/false/undef; a type attr -> None
        return None

    def ports(method, count):
        if method in _PORTS:
            return _PORTS[method]
        return ["a", "b"] if count == 2 else [f"in{i}" for i in range(count)]

    def connect(src, dst, port):
        if src is None:
            return
        ensure(src)
        edges.append({"from": src, "to": dst, "port": port})

    for idx, (method, args, _kwargs) in enumerate(calls):
        net = idx2net.get(idx)

        if method == "set_latch_init_next":
            latch = as_net(args[0])
            if latch is not None:
                connect(as_net(args[1]), latch, "init")
                connect(as_net(args[2]), latch, "next")
            continue
        if method == "mk_output" or net is None:
            continue  # outputs are flagged from context.outputs; ignore other non-net calls
        if method == "mk_input":
            node(net, "input", type_=_type_name(args[1]))
            continue
        if method == "mk_latch":
            node(net, "latch", type_=_type_name(args[1]))
            continue
        if method == "mk_number":
            node(net, "const", type_=_type_name(args[1]), value=str(args[0][1]))
            continue
        if method in ("mk_true", "mk_false"):
            label = method[3:]
            node(net, "const", op=label, value=label)
            continue

        op = method[3:] if method.startswith("mk_") else method
        node(net, "gate", op=op)
        for port, arg in zip(ports(method, len(args)), args):
            connect(as_net(arg), net, port)

    for net in output_nets:
        ensure(net)
        nodes[net]["output"] = True

    return {"version": 1,
            "nodes": [nodes[net] for net in sorted(nodes)],
            "edges": edges}


def _type_name(ref):
    """The readable type of a ('attr', '<...>type') reference, else None."""
    return _TYPE_ATTR_TO_NAME.get(ref[1]) if ref[0] == "attr" else None


def main(argv=None):
    """``python -m intrepyd.export program.py [-o out.json]``: run the program and
    export the circuit of the context it builds (the one with the most nets, if
    it builds several) to ``out.json`` or standard output."""
    parser = argparse.ArgumentParser(description="Export an intrepyd circuit as a JSON graph.")
    parser.add_argument("program", help="a python program that builds a Context")
    parser.add_argument("-o", "--out", help="write here instead of standard output")
    parser.add_argument("--all", action="store_true",
                        help="export every context built, as a JSON list")
    args = parser.parse_args(argv)

    # Imported late, on purpose: it needs the native library, which neither the
    # exporter nor its tests require.
    from intrepyd import context as context_module  # pylint: disable=import-outside-toplevel

    built = []
    original_init = context_module.Context.__init__

    def tracking_init(self, *a, **k):
        original_init(self, *a, **k)
        built.append(self)

    context_module.Context.__init__ = tracking_init
    try:
        runpy.run_path(args.program, run_name="__main__")
    finally:
        context_module.Context.__init__ = original_init

    if not built:
        sys.exit(f"Error: {args.program} built no Context")
    if args.all:
        payload = json.dumps([to_graph(ctx) for ctx in built], indent=2)
    else:
        payload = to_json(max(built, key=lambda ctx: len(ctx.net2name)))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
