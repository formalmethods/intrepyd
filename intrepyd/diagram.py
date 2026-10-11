"""
Builds and simulates a circuit drawn as a *diagram*: the documents of the
intrepid-vscode circuit editor (``*.intrepyd.json``). It is the inverse of
``intrepyd.export``: the export turns a ``Context`` into a netlist, this turns a
netlist (with the editor's own blocks) back into a ``Context``, ready to be
simulated or verified.

Diagram format (version 3)
--------------------------

::

    {
      "format": "intrepyd-diagram",
      "version": 3,
      "circuit": {
        "nodes": [ ... ],   # intrepyd.export's nodes, plus the editor's blocks
        "edges": [ ... ]    # {"from", "to", "port"[, "fromPort"]}
      },
      "layout": { ... },    # the drawing, ignored here
      "simulation": {       # optional: what Simulate runs
        "steps": 10,
        "stimuli": { "<input block id>": ["true", "false", ...], ... }
      },
      "verification": {     # optional: how Verify runs
        "engine": "portfolio",  # or one engine: bmc, kind, br, pdr
        "timeout": 30,          # seconds, per property
        "depth": 50             # the deepest depth bmc and kind try (optional)
      }
    }

On top of the export's schema, a diagram has:

- ``"kind": "output"`` blocks (an output, named, with one input ``in``);
- ``"kind": "component"`` blocks, a block of ``intrepyd.lib`` (``"module"``,
  ``"symbol"``, ``"params"``); a wire's ``"fromPort"`` picks which of a
  block's outputs it carries (absent: the block's primary output);
- ``"inputs"`` on an and/or/xor/add/mul gate drawn with more than two inputs
  (``in0``, ``in1``, ...), built as a chain of binary calls;
- the properties to verify: ``"kind": "assertion"`` (its boolean input must
  always hold) and ``"kind": "target"`` (a boolean condition to reach), each
  named, with one input ``in``.

Command line
------------

``python -m intrepyd.diagram simulate FILE`` (``-`` reads standard input)
simulates the diagram's ``simulation`` section (``--steps`` overrides the number
of steps) and prints, as JSON::

    {"steps": N, "values": {"<block id>.<output>": ["T", "F", ...], ...}}

with one entry per output of every block (booleans as ``T``/``F``, numbers as
the trace prints them).

``python -m intrepyd.diagram verify FILE`` checks each property on its own
(``--engine``, ``--timeout``, ``--depth`` override the diagram's
``verification`` section) and prints::

    {"results": [{"block": id, "kind": "assertion", "name": "safe",
                  "verdict": "holds" | "fails" | "reached" | "unreachable" | "unknown",
                  "engine": "pdr", "time": 0.12,
                  "trace": {"steps": N, "values": {...}, "stimuli": {...}}}, ...]}

An assertion *holds* or *fails*; a target is *reached* or *unreachable*;
*unknown* when no engine answers in time. A failing assertion or a reached
target carries its trace: the inputs that lead there (``stimuli``, as the
simulation section takes them) and every block's values along it, its last
step being where the assertion fails or the target is reached.

On an error both commands print the reason to standard error and exit with
status 1.
"""

import argparse
import json
import sys

FORMAT = "intrepyd-diagram"
VERSION = 3

_TYPE_MAKERS = {
    "bool": "mk_boolean_type",
    "int8": "mk_int8_type", "int16": "mk_int16_type", "int32": "mk_int32_type",
    "int64": "mk_int64_type",
    "uint8": "mk_uint8_type", "uint16": "mk_uint16_type", "uint32": "mk_uint32_type",
    "uint64": "mk_uint64_type",
    "real": "mk_real_type",
    "float16": "mk_float16_type", "float32": "mk_float32_type", "float64": "mk_float64_type",
    "int": "mk_int_type",
}

_UNARY = {"not", "minus"}
_VARIADIC = {"and", "or", "xor", "add", "mul"}

# The library blocks: how to call each one. A call argument is "ctx", "name",
# ("in", port) a wired input, ("type", key) a type parameter or ("int", key) an
# integer one. A function returns its outputs (a tuple when several); a class
# is built, then closed with set_init_next(...), and its outputs are attributes.
_IN = "in"
_LIBRARY = {
    "mk_mux": {"module": "eda", "ctor": ["ctx", (_IN, "sel"), (_IN, "in0"), (_IN, "in1")],
               "name_kw": True, "outputs": 1},
    "mk_clock": {"module": "eda", "ctor": ["ctx", "name"], "outputs": 2},
    "mk_counter": {"module": "eda", "ctor": ["ctx", "name", ("type", "t"), (_IN, "limit")],
                   "outputs": 2, "defaults": {"t": "int8"}},
    "LatchD": {"module": "eda", "ctor": ["ctx", "name", ("type", "t")],
               "setnext": [(_IN, "init"), (_IN, "d"), (_IN, "e")], "attrs": ["q"]},
    "Delay": {"module": "eda", "ctor": ["ctx", "name", ("type", "t")],
              "setnext": [(_IN, "init"), (_IN, "d")], "attrs": ["q"]},
    "FlipFlopD": {"module": "eda", "ctor": ["ctx", "name", ("type", "t"), (_IN, "c")],
                  "setnext": [(_IN, "init"), (_IN, "d")], "attrs": ["q"]},
    "FlipFlopDE": {"module": "eda", "ctor": ["ctx", "name", ("type", "t"), (_IN, "c")],
                   "setnext": [(_IN, "init"), (_IN, "d"), (_IN, "e")], "attrs": ["q"]},
    "ShiftRegister": {"module": "eda", "ctor": ["ctx", "name", ("type", "t"), ("int", "length")],
                      "setnext": [(_IN, "init"), (_IN, "d")], "attrs": ["q"],
                      "defaults": {"length": "3"}},
    "mk_r_trig": {"module": "plc", "ctor": ["ctx", (_IN, "clk"), "name"], "outputs": 1},
    "mk_f_trig": {"module": "plc", "ctor": ["ctx", (_IN, "clk"), "name"], "outputs": 1},
    "mk_sr": {"module": "plc", "ctor": ["ctx", (_IN, "s"), (_IN, "r"), "name"], "outputs": 1},
    "mk_rs": {"module": "plc", "ctor": ["ctx", (_IN, "s"), (_IN, "r"), "name"], "outputs": 1},
    "mk_ctu": {"module": "plc", "ctor": ["ctx", "name", (_IN, "cu"), (_IN, "reset"), (_IN, "pv"),
                                         ("type", "typ")], "outputs": 2, "primary": 1},
    "mk_ctd": {"module": "plc", "ctor": ["ctx", "name", (_IN, "cd"), (_IN, "load"), (_IN, "pv"),
                                         ("type", "typ")], "outputs": 2, "primary": 1},
    "mk_ctud": {"module": "plc", "ctor": ["ctx", "name", (_IN, "cu"), (_IN, "cd"), (_IN, "reset"),
                                          (_IN, "load"), (_IN, "pv"), ("type", "typ")],
                "outputs": 3, "primary": 1},
    "mk_ton": {"module": "plc", "ctor": ["ctx", "name", (_IN, "in"), (_IN, "pt"), ("type", "typ")],
               "outputs": 2, "primary": 1},
    "mk_tof": {"module": "plc", "ctor": ["ctx", "name", (_IN, "in"), (_IN, "pt"), ("type", "typ")],
               "outputs": 2, "primary": 1},
    "mk_tp": {"module": "plc", "ctor": ["ctx", "name", (_IN, "in"), (_IN, "pt"), ("type", "typ")],
              "outputs": 2, "primary": 1},
}
_TYPE_DEFAULTS = {"t": "bool", "typ": "int8"}


class DiagramError(ValueError):
    """A diagram that cannot be built, with a reason a user can read."""


class Circuit:  # pylint: disable=too-few-public-methods
    """A diagram built in a Context: the context, the net of each block output
    (``outputs[(block id, output index)]``) and the net of each input block
    (``inputs[block id]``)."""

    def __init__(self, ctx, inputs, outputs):
        self.ctx = ctx
        self.inputs = inputs
        self.outputs = outputs
        self.properties = []  # (assertion or target block, the net it checks)


def load(source):
    """A diagram from a path, a file object, a JSON string or a dict, checked to
    be an intrepyd diagram of the version this module reads."""
    if isinstance(source, dict):
        data = source
    elif hasattr(source, "read"):
        data = json.loads(source.read())
    elif isinstance(source, str) and source.lstrip().startswith("{"):
        data = json.loads(source)
    else:
        with open(source, encoding="utf-8") as handle:
            data = json.load(handle)
    if data.get("format") != FORMAT:
        raise DiagramError(f'not an intrepyd diagram (expected "format": "{FORMAT}")')
    if data.get("version") != VERSION:
        raise DiagramError(
            f"unsupported diagram version {data.get('version')}; this reads {VERSION}")
    return data


def build(diagram, ctx=None):
    """Builds the circuit of a diagram (see ``load``) in ``ctx`` (a new Context if
    None) and returns a ``Circuit``. Raises ``DiagramError`` if a block is
    unknown or an input is not wired; intrepyd's own errors (a type mismatch)
    propagate."""
    if ctx is None:
        from intrepyd.context import Context  # pylint: disable=import-outside-toplevel
        ctx = Context()
    return _Builder(diagram, ctx).run()


def simulate(diagram, steps=None, stimuli=None):
    """Simulates a diagram for ``steps`` steps with ``stimuli`` (input block id ->
    the value at each step, as the editor writes them: "true"/"false", numbers),
    by default its ``simulation`` section. Returns ``{"steps": n, "values":
    {"<id>.<output>": [value at step 0, ...]}}``."""
    section = diagram.get("simulation") or {}
    steps = int(steps if steps is not None else section.get("steps", 10))
    if steps < 1:
        raise DiagramError("simulate at least one step")
    stimuli = stimuli if stimuli is not None else section.get("stimuli", {})
    circuit = build(diagram)
    simulator = circuit.ctx.mk_simulator()
    for net in sorted(set(circuit.outputs.values())):
        simulator.add_watch(net)
    trace = circuit.ctx.mk_trace()
    for key, values in stimuli.items():
        net = circuit.inputs.get(int(key))
        if net is None:
            continue  # a stimulus left over for an input since deleted
        for depth, value in enumerate(list(values)[:steps]):
            if value not in (None, ""):
                trace.set_value(net, depth, _stimulus_value(value))
    simulator.simulate(trace, steps - 1)
    values = {f"{block}.{index}": [trace.get_value(net, d) for d in range(steps)]
              for (block, index), net in sorted(circuit.outputs.items())}
    return {"steps": steps, "values": values}


def _stimulus_value(value):
    text = str(value).strip()
    lowered = text.lower()
    if lowered in ("true", "t"):
        return "true"
    if lowered in ("false", "f"):
        return "false"
    return text


ENGINES = ("portfolio", "bmc", "kind", "br", "pdr")


def verify(diagram, engine=None, timeout=None, depth=None):
    """Checks each property of a diagram (its assertion and target blocks) on its
    own, with ``engine`` (the portfolio, or one engine), ``timeout`` seconds each
    and, for bmc and kind, at most ``depth`` steps — by default the diagram's
    ``verification`` section. Returns ``{"results": [...]}`` (see the module
    documentation): a verdict per property, and the trace of a failing
    assertion or a reached target."""
    section = diagram.get("verification") or {}
    engine = engine or section.get("engine", "portfolio")
    if engine not in ENGINES:
        raise DiagramError(f'unknown engine "{engine}"; one of {", ".join(ENGINES)}')
    timeout = float(timeout if timeout is not None else section.get("timeout", 30))
    depth = depth if depth is not None else section.get("depth")
    circuit = build(diagram)
    if not circuit.properties:
        raise DiagramError("the circuit has no assertion and no target to verify")
    engines = None if engine == "portfolio" else [engine]
    return {"results": [_check(diagram, circuit, node, net, (engines, depth, timeout))
                        for node, net in circuit.properties]}


def _check(diagram, circuit, node, net, how):  # pylint: disable=too-many-locals
    """One property's verdict (and trace), by its own run of the engines."""
    from intrepyd.engine import EngineResult  # pylint: disable=import-outside-toplevel
    engines, depth, timeout = how
    assertion = node["kind"] == "assertion"
    target = circuit.ctx.mk_not(net) if assertion else net
    portfolio = circuit.ctx.mk_portfolio(engines=engines, max_depth=depth)
    portfolio.add_target(target)
    # the inputs, to replay the trace; the target too, which reaches the
    # failing step even in a circuit without inputs
    for watched in [*circuit.inputs.values(), target]:
        portfolio.add_watch(watched)
    answer = portfolio.reach_targets(timeout=timeout)
    entry = {"block": node["id"], "kind": node["kind"], "name": node.get("name"),
             "engine": portfolio.get_last_engine(), "time": round(portfolio.get_last_time(), 3)}
    if answer == EngineResult.REACHABLE:
        entry["verdict"] = "fails" if assertion else "reached"
        entry["trace"] = _replay(diagram, circuit, portfolio.get_last_trace())
    elif answer == EngineResult.UNREACHABLE:
        entry["verdict"] = "holds" if assertion else "unreachable"
    else:
        entry["verdict"] = "unknown"
        errors = portfolio.get_last_errors()
        if errors:
            entry["errors"] = errors
    return entry


def _replay(diagram, circuit, trace):
    """A counterexample as the editor shows it: the inputs at each step (as
    stimuli), and every block's values along it, by simulating those inputs."""
    steps = trace.get_max_depth() + 1
    stimuli = {}
    for block, net in circuit.inputs.items():
        row = []
        for depth in range(steps):
            value = trace.get_value(net, depth)
            row.append("true" if value == "T" else "false" if value == "F"
                       else "" if value == "?" else value)
        stimuli[str(block)] = row
    simulated = simulate(diagram, steps=steps, stimuli=stimuli)
    return {"steps": steps, "values": simulated["values"], "stimuli": stimuli}


# --- the builder ---------------------------------------------------------------------

class _Builder:  # pylint: disable=too-few-public-methods,too-many-instance-attributes

    def __init__(self, diagram, ctx):
        circuit = diagram.get("circuit") or {}
        self.ctx = ctx
        self.nodes = {n["id"]: n for n in circuit.get("nodes", [])}
        self.into = {}
        for edge in circuit.get("edges", []):
            self.into.setdefault(edge["to"], {})[edge["port"]] = edge
        self.types = {}
        self.outputs = {}
        self.inputs = {}
        self.objects = {}  # library class instances, by block id
        self.properties = []  # (block, the net it checks), in id order

    def run(self):
        """Builds every block in dependency order, then closes the feedback."""
        for node in self._order():
            self._make(node)
        for node in self.nodes.values():
            self._close(node)
        circuit = Circuit(self.ctx, self.inputs, self.outputs)
        circuit.properties = self.properties
        return circuit

    # -- what a block is ----------------------------------------------------------------

    def _ports(self, node):  # pylint: disable=too-many-return-statements
        kind = node["kind"]
        if kind == "latch":
            return ["init", "next"]
        if kind in ("output", "assertion", "target"):
            return ["in"]
        if kind == "component":
            spec = self._spec(node)
            return [a[1] for a in spec["ctor"] + spec.get("setnext", [])
                    if isinstance(a, tuple) and a[0] == _IN]
        if kind == "gate":
            op = node.get("op", "")
            if op == "ite":
                return ["if", "then", "else"]
            if op in _UNARY or op.startswith("cast_to_"):
                return ["in"]
            count = node.get("inputs", 2) if op in _VARIADIC else 2
            return [f"in{i}" for i in range(count)] if count > 2 else ["a", "b"]
        return []

    def _deferred(self, node):
        """Inputs supplied after the block is built: they may be feedback."""
        if node["kind"] == "latch":
            return {"init", "next"}
        if node["kind"] == "component":
            return {a[1] for a in self._spec(node).get("setnext", []) if isinstance(a, tuple)}
        return set()

    def _spec(self, node):
        spec = _LIBRARY.get(node.get("symbol"))
        if spec is None:
            raise DiagramError(f'{_label(node)}: unknown library block "{node.get("symbol")}"')
        return spec

    def _order(self):
        """Blocks in dependency order; feedback (a latch's init/next, a library
        block's set_init_next) does not count."""
        pending = {nid: set() for nid in self.nodes}
        users = {nid: [] for nid in self.nodes}
        for nid, ports in self.into.items():
            node = self.nodes.get(nid)
            if node is None:
                continue
            deferred = self._deferred(node)
            for port, edge in ports.items():
                if port not in deferred and edge["from"] in self.nodes:
                    pending[nid].add(edge["from"])
                    users[edge["from"]].append(nid)
        ready = sorted(nid for nid, deps in pending.items() if not deps)
        order = []
        while ready:
            nid = ready.pop(0)
            order.append(self.nodes[nid])
            for user in users[nid]:
                pending[user].discard(nid)
                if not pending[user] and user not in ready and self.nodes[user] not in order:
                    ready.append(user)
                    ready.sort()
        if len(order) < len(self.nodes):
            looped = sorted(set(self.nodes) - {n["id"] for n in order})
            names = ", ".join(_label(self.nodes[n]) for n in looped)
            raise DiagramError(f"combinational loop through {names}")
        return order

    # -- building -------------------------------------------------------------------------

    def _type(self, name):
        if name not in self.types:
            maker = _TYPE_MAKERS.get(name)
            if maker is None:
                raise DiagramError(f'unknown type "{name}"')
            self.types[name] = getattr(self.ctx, maker)()
        return self.types[name]

    def _input(self, node, port):
        """The net wired into a block's input."""
        edge = self.into.get(node["id"], {}).get(port)
        if edge is None:
            raise DiagramError(f'{_label(node)}: input "{port}" is not wired')
        source = self.nodes.get(edge["from"])
        if source is None:
            raise DiagramError(f"{_label(node)}: input \"{port}\" is wired from a missing block")
        index = edge.get("fromPort", _primary(source))
        net = self.outputs.get((source["id"], index))
        if net is None:
            raise DiagramError(f'{_label(node)}: input "{port}" comes from {_label(source)}, '
                               f"which has no output {index}")
        return net

    def _make(self, node):  # pylint: disable=too-many-branches
        kind = node["kind"]
        nid = node["id"]
        name = node.get("name")
        ctx = self.ctx
        if kind == "input":
            net = ctx.mk_input(name, self._type(node.get("type", "bool")))
            self.inputs[nid] = net
        elif kind == "latch":
            net = ctx.mk_latch(name, self._type(node.get("type", "bool")))
        elif kind == "const":
            net = self._constant(node)
        elif kind == "gate":
            net = self._gate(node)
        elif kind == "component":
            self._component(node)
            return
        else:
            return  # an output is tagged at the end; anything else has no net
        self.outputs[(nid, 0)] = net

    def _constant(self, node):
        value = str(node.get("value", node.get("op", "")))
        if node.get("op") == "true" or value == "true":
            return self.ctx.mk_true()
        if node.get("op") == "false" or value == "false":
            return self.ctx.mk_false()
        if value == "?":
            return self.ctx.mk_undef()
        return self.ctx.mk_number(value, self._type(node.get("type", "int")))

    def _gate(self, node):
        op = node.get("op", "")
        args = [self._input(node, port) for port in self._ports(node)]
        named = {"name": node["name"]} if node.get("name") else {}
        maker = getattr(self.ctx, f"mk_{op}", None)
        if maker is None:
            raise DiagramError(f'{_label(node)}: unknown operator "{op}"')
        if op in _VARIADIC and len(args) > 2:
            net = args[0]
            for arg in args[1:-1]:
                net = maker(net, arg)
            return maker(net, args[-1], **named)
        return maker(*args, **named)

    def _component(self, node):
        spec = self._spec(node)
        module = __import__(f"intrepyd.lib.{spec['module']}", fromlist=[node["symbol"]])
        call = getattr(module, node["symbol"])
        args, kwargs = [], {}
        for arg in spec["ctor"]:
            args.append(self._argument(node, spec, arg))
        if spec.get("name_kw") and node.get("name"):
            kwargs["name"] = node["name"]
        result = call(*args, **kwargs)
        nid = node["id"]
        if "attrs" in spec:
            self.objects[nid] = result
            for index, attr in enumerate(spec["attrs"]):
                self.outputs[(nid, index)] = getattr(result, attr)
        elif spec["outputs"] == 1:
            self.outputs[(nid, 0)] = result
        else:
            for index, net in enumerate(result):
                self.outputs[(nid, index)] = net

    def _argument(self, node, spec, arg):
        params = node.get("params") or {}
        defaults = {**_TYPE_DEFAULTS, **spec.get("defaults", {})}
        if arg == "ctx":
            return self.ctx
        if arg == "name":
            return node.get("name") or f"{node['symbol']}_{node['id']}"
        kind, key = arg
        if kind == _IN:
            return self._input(node, key)
        if kind == "type":
            return self._type(params.get(key, defaults.get(key, "bool")))
        return int(params.get(key, defaults.get(key, "1")))

    def _close(self, node):
        """Feedback and outputs, once every net exists."""
        kind = node["kind"]
        if kind == "latch":
            latch = self.outputs[(node["id"], 0)]
            self.ctx.set_latch_init_next(latch, self._input(node, "init"),
                                         self._input(node, "next"))
        elif kind == "component" and "setnext" in self._spec(node):
            spec = self._spec(node)
            obj = self.objects[node["id"]]
            obj.set_init_next(*[self._argument(node, spec, arg) for arg in spec["setnext"]])
        elif kind == "output":
            self.ctx.mk_output(self._input(node, "in"), node.get("name"))
        elif kind in ("assertion", "target"):
            self.properties.append((node, self._input(node, "in")))
        if node.get("output") and kind != "output":
            self.ctx.mk_output(self.outputs[(node["id"], 0)], node.get("name"))


def _primary(node):
    if node.get("kind") == "component":
        return _LIBRARY.get(node.get("symbol"), {}).get("primary", 0)
    return 0


def _label(node):
    kind = node.get("kind")
    what = node.get("op") if kind == "gate" else node.get("symbol") if kind == "component" else kind
    name = node.get("name")
    return f'{what} "{name}"' if name else f"{what} {node.get('id')}"


# --- command line ------------------------------------------------------------------------

def main(argv=None):
    """``python -m intrepyd.diagram simulate|verify FILE|- [options]``"""
    parser = argparse.ArgumentParser(prog="python -m intrepyd.diagram",
                                     description="Simulate or verify an intrepyd circuit diagram.")
    sub = parser.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate", help="simulate the diagram's stimuli, print the trace as JSON")
    sim.add_argument("diagram", help="a *.intrepyd.json file, or - for standard input")
    sim.add_argument("--steps", type=int, help="the number of steps (default: the diagram's)")
    ver = sub.add_parser("verify", help="check the diagram's assertions and targets, print JSON")
    ver.add_argument("diagram", help="a *.intrepyd.json file, or - for standard input")
    ver.add_argument("--engine", choices=ENGINES, help="default: the diagram's, else portfolio")
    ver.add_argument("--timeout", type=float, help="seconds per property (default: 30)")
    ver.add_argument("--depth", type=int, help="the deepest depth bmc and kind try")
    args = parser.parse_args(argv)
    try:
        diagram = load(sys.stdin if args.diagram == "-" else args.diagram)
        if args.command == "verify":
            result = verify(diagram, engine=args.engine, timeout=args.timeout, depth=args.depth)
        else:
            result = simulate(diagram, steps=args.steps)
    except Exception as err:  # pylint: disable=broad-except  # reported, not raised, to the editor
        sys.stderr.write(f"{type(err).__name__}: {err}\n")
        return 1
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
