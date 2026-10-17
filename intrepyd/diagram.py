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
        "depth": 50,            # the deepest depth bmc and kind try (optional)
        "certificates": false   # proof certificates for what is proved (optional)
      },
      "testgen": {          # optional: the MC/DC tests to generate
        "decisions": [{"block": 7, "stops": [5], "start": 2}, ...],
        "timeout": 30,          # seconds, per condition
        "depth": 20             # the longest test, in steps after the first
      },
      "requirement": {      # optional: the requirement the circuit implements
        "id": "LLR-012",
        "title": "Alarm on occlusion",
        "text": "The pump shall raise the occlusion alarm when ...",
        "signals": {"pressure": "int16"},
        "formula": "(pressure > 300 and infusing) or door_open",
        "built": {...}          # what the editor last built the circuit from
      }
    }

The ``requirement`` section is the editor's: the circuit a requirement's
formula is built into is an ordinary circuit, in ``circuit``, and this module
builds, simulates and verifies it, and generates its MC/DC tests, as any
other. The section itself is not read here.

On top of the export's schema, a diagram has:

- ``"kind": "output"`` blocks (an output, named, with one input ``in``);
- ``"kind": "component"`` blocks, a block of ``intrepyd.lib`` (``"module"``,
  ``"symbol"``, ``"params"``); a wire's ``"fromPort"`` picks which of a
  block's outputs it carries (absent: the block's primary output);
- ``"inputs"`` on an and/or/xor/add/mul gate drawn with more than two inputs
  (``in0``, ``in1``, ...), built as a chain of binary calls;
- the properties to verify: ``"kind": "assertion"`` (its boolean input must
  always hold) and ``"kind": "target"`` (a boolean condition to reach), each
  named, with one input ``in``;
- ``"kind": "assumption"`` blocks (named, one boolean input ``in``): a
  condition the inputs are constrained to at every step, as a Lustre model's
  ``assert``; verifying and the MC/DC tests consider only the runs where
  every assumption holds (simulating does not check them);
- ``"kind": "subsystem"`` blocks, a part of the circuit drawn as one block: the
  blocks inside it have ``"parent": <its id>`` (ids are unique in the whole
  diagram, and a wire joins two blocks of one sub-system, or two at the top).
  Its In blocks are its inputs, wired from outside by their name
  (``"port": "<the In block's name>"``), and its Out blocks its outputs, in id
  order (``"fromPort": 0, 1, ...``). Sub-systems nest. The names of the blocks
  inside are prefixed with the sub-system's (``"filter.acc"``) when built.

The library blocks are those of ``intrepyd.lib.catalogue``, which describes
each one (its parameters, pins, outputs and types).

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
*unknown* when no engine answers in time. With ``--certificates`` (or
``"certificates": true``), a property that holds or a target unreachable also
has a ``"certificate"``: the proof, an SMT-LIB 2 script each of whose
``check-sat`` must answer ``unsat``, which any SMT solver can run to check it
(``null`` when the engine that proved it gives none). The proof is checked by
intrepid before it is given; one that does not hold makes the verdict
*unknown*. Certificates need intrepid 1.4 or newer. A failing assertion or a reached
target carries its trace: the inputs that lead there (``stimuli``, as the
simulation section takes them) and every block's values along it, its last
step being where the assertion fails or the target is reached.

In a simulation, the outputs of a sub-system carry the values of its Out blocks.

``python -m intrepyd.diagram mcdc FILE`` generates MC/DC tests (Modified
Condition / Decision Coverage) for the decisions of the diagram's ``testgen``
section (``--decision ID``, repeated, ``--depth`` and ``--timeout`` override
it). A decision is a block with a boolean output (an Out, Assertion or Target
block stands for what is wired into it); its *conditions* are found by walking
back from it through the boolean operators (and, or, not, xor, iff, implies,
ite) and the pins of sub-systems, down to the first net that is none of them:
an input, a latch, a comparison, the output of a library block, or a block
listed in the decision's ``"stops"``. Constants are not conditions, and a net
reached twice is one condition. For each condition, the tests are a pair that
shows it alone decides the outcome (masking MC/DC): the condition and the
decision differ between the two tests, and in each the decision would change
if the condition did. A decision's ``"start"`` (0 by default) is the first
step at which it counts: every test then has at least start + 1 steps (a
circuit that is late by some steps, as one computing a formula that looks
ahead, says nothing at its first ones). It prints::

    {"criterion": "masking", "results": [{
        "decision": id, "name": "and1",
        "conditions": [{"block": id, "output": 0, "name": "in1",
                        "status": "covered" | "unreachable" | "unknown",
                        "pair": [0, 1], "engine": "bmc", "time": 0.1}, ...],
        "tests": [{"steps": N, "stimuli": {...}, "values": {...},
                   "conditions": ["T", "F", ...], "decision": "T"}, ...],
        "covered": 2, "total": 2, "start": 2}, ...]}

(``start`` only when the decision has one.)

Each test is a run of the circuit (its inputs at each step, as stimuli, and
every block's values along it, as a simulation gives them); its conditions
and its decision are read at its last step. A condition is *unreachable* when
no pair of tests can show it decides the decision (it is masked, or the logic
around it is redundant), *unknown* when none was found within the depth and
the timeout. The tests are not a minimal set: two conditions may share a test
only when they happen to.

``python -m intrepyd.diagram catalogue`` prints the library blocks a diagram may
use (``intrepyd.lib.catalogue``), as JSON.

On an error the commands print the reason to standard error and exit with
status 1.
"""

import argparse
import json
import sys

from intrepyd.lib import catalogue

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
        self.aliases = {}  # (sub-system id, output index) -> the Out block inside
        self.input_types = {}  # input block id -> its type's name


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
    # a sub-system's outputs carry what its Out blocks inside do
    for (block, index), out in sorted(circuit.aliases.items()):
        if f"{out}.0" in values:
            values[f"{block}.{index}"] = values[f"{out}.0"]
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


def verify(diagram, engine=None, timeout=None, depth=None, certificates=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Checks each property of a diagram (its assertion and target blocks) on its
    own, with ``engine`` (the portfolio, or one engine), ``timeout`` seconds each
    and, for bmc and kind, at most ``depth`` steps — by default the diagram's
    ``verification`` section. Returns ``{"results": [...]}`` (see the module
    documentation): a verdict per property, and the trace of a failing
    assertion or a reached target. With ``certificates``, a proved property
    comes with its proof certificate."""
    section = diagram.get("verification") or {}
    engine = engine or section.get("engine", "portfolio")
    if engine not in ENGINES:
        raise DiagramError(f'unknown engine "{engine}"; one of {", ".join(ENGINES)}')
    timeout = float(timeout if timeout is not None else section.get("timeout", 30))
    depth = depth if depth is not None else section.get("depth")
    if certificates is None:
        certificates = section.get("certificates", False)
    certificates = bool(certificates)
    if certificates:
        from intrepyd import api  # pylint: disable=import-outside-toplevel
        if not api.HAS_CERTIFICATES:
            raise DiagramError("proof certificates need intrepid 1.4 or newer, and the library "
                               f"of this intrepyd is older ({api.LIBRARY_PATH})")
    circuit = build(diagram)
    if not circuit.properties:
        raise DiagramError("the circuit has no assertion and no target to verify")
    engines = None if engine == "portfolio" else [engine]
    return {"results": [_check(diagram, circuit, node, net, (engines, depth, timeout, certificates))
                        for node, net in circuit.properties]}


def _check(diagram, circuit, node, net, how):  # pylint: disable=too-many-locals
    """One property's verdict (and trace), by its own run of the engines."""
    from intrepyd.engine import EngineResult  # pylint: disable=import-outside-toplevel
    engines, depth, timeout, certificates = how
    assertion = node["kind"] == "assertion"
    target = circuit.ctx.mk_not(net) if assertion else net
    portfolio = circuit.ctx.mk_portfolio(engines=engines, max_depth=depth,
                                         certificates=certificates)
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
        if certificates:
            entry["certificate"] = portfolio.get_last_certificate()
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
    stimuli = _stimuli(circuit, trace, steps)
    simulated = simulate(diagram, steps=steps, stimuli=stimuli)
    return {"steps": steps, "values": simulated["values"], "stimuli": stimuli}


def _stimuli(circuit, trace, steps):
    """The inputs of ``circuit`` along a trace an engine found, as stimuli. An
    input the trace leaves free (what is found holds whatever it is) takes
    false, or 0: the stimuli are concrete, and have no gap (an input with no
    value at a step but one at a later step, which crashes the simulator of
    the intrepid libraries up to 1.5.0)."""
    stimuli = {}
    for block, net in circuit.inputs.items():
        free = "false" if circuit.input_types.get(block, "bool") == "bool" else "0"
        row = []
        for depth in range(steps):
            value = trace.get_value(net, depth)
            row.append("true" if value == "T" else "false" if value == "F"
                       else free if value == "?" else value)
        stimuli[str(block)] = row
    return stimuli


# --- MC/DC test generation ----------------------------------------------------------------

CRITERION = "masking"

# The operators a decision is walked back through: the rest are conditions.
_BOOLEAN_OPS = {"and", "or", "not", "xor", "iff", "implies", "ite"}


def conditions(diagram, decision, stops=()):
    """The conditions of a decision: walking back from block ``decision``
    through the boolean operators and the pins of sub-systems, the first nets
    that are none of them, or blocks of ``stops`` (see the module
    documentation). Returns ``[{"block": id, "output": index, "name": ...}]``,
    in the order they are met, the inputs of a block in pin order."""
    nodes, into, _ = _netlist(diagram)
    start = _decision_source(nodes, into, decision)
    return [{"block": nid, "output": index, "name": _net_name(nodes[nid])}
            for nid, index in _walk(nodes, into, start, set(stops))]


def _decision_source(nodes, into, decision):
    """The net a decision block stands for, as (block id, output index)."""
    node = nodes.get(decision)
    if node is None:
        raise DiagramError(f"no block {decision} to be a decision (a sub-system is not one: "
                           "pick a block inside it, or the block it drives)")
    if node["kind"] in ("output", "assertion", "target", "assumption"):
        return _source(nodes, into, node, "in")
    return (decision, _primary(node))


def _source(nodes, into, node, port):
    edge = into.get(node["id"], {}).get(port)
    if edge is None or edge["from"] not in nodes:
        raise DiagramError(f'{_label(node)}: input "{port}" is not wired')
    return (edge["from"], edge.get("fromPort", _primary(nodes[edge["from"]])))


def _walk(nodes, into, start, stops):
    found, seen, pending = [], set(), [start]
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        node = nodes[key[0]]
        if key != start and key[0] in stops:
            found.append(key)
        elif node["kind"] == "via":
            pending.append(_source(nodes, into, node, "in"))
        elif node["kind"] == "gate" and node.get("op") in _BOOLEAN_OPS:
            # depth first, the first pin first
            pending.extend(reversed([_source(nodes, into, node, p) for p in _gate_ports(node)]))
        elif node["kind"] != "const":
            found.append(key)
    return found


def _net_name(node):
    return node.get("name") or _label(node)


def mcdc(diagram, decisions=None, depth=None, timeout=None):
    """Generates MC/DC tests for ``decisions`` (block ids, or ``{"block": id,
    "stops": [...]}``), by default those of the diagram's ``testgen`` section,
    each test at most ``depth`` steps after the first, ``timeout`` seconds per
    condition. Returns ``{"criterion": "masking", "results": [...]}`` (see the
    module documentation)."""
    section = diagram.get("testgen") or {}
    entries = decisions if decisions is not None else section.get("decisions", [])
    entries = [e if isinstance(e, dict) else {"block": e} for e in entries]
    if not entries:
        raise DiagramError("choose a decision to generate MC/DC tests for")
    depth = int(depth if depth is not None else section.get("depth", 20))
    timeout = float(timeout if timeout is not None else section.get("timeout", 30))
    return {"criterion": CRITERION,
            "results": [_mcdc_decision(diagram, int(e["block"]), e.get("stops", ()),
                                       (depth, timeout, int(e.get("start", 0)))) for e in entries]}


def _mcdc_decision(diagram, decision, stops, how):  # pylint: disable=too-many-locals
    """The tests of one decision: a pair per condition, searched on two copies
    of the circuit, A and B, side by side."""
    from intrepyd.context import Context  # pylint: disable=import-outside-toplevel
    from intrepyd.engine import EngineResult  # pylint: disable=import-outside-toplevel
    depth, timeout, start = how
    if start < 0:
        raise DiagramError(f"the start of decision {decision} is a step, 0 or more")
    if start > depth:
        raise DiagramError(f"decision {decision} starts at step {start}, after the longest test "
                           f"({depth} steps after the first): make the tests longer")
    nodes, into, _ = _netlist(diagram)
    key = _decision_source(nodes, into, decision)
    found = _walk(nodes, into, key, set(stops))
    ctx = Context()
    a = _copy(diagram, ctx, "A")
    b = _copy(diagram, ctx, "B")
    if a.outputs.get(key) is None:
        raise DiagramError(f"{_label(nodes[decision])} has no output to be a decision")
    type_ = ctx._net2type.get(a.outputs[key])  # pylint: disable=protected-access
    if type_ is not None and type_ != ctx.mk_boolean_type():
        raise DiagramError(f"{_label(nodes[decision])} is not a boolean: it cannot be a decision")
    tests, index = [], {}
    rows = []
    counts = _from_step(ctx, start)
    for cond in found:
        objective = _objective(ctx, a.outputs[key], b.outputs[key],
                               a.outputs[cond], b.outputs[cond])
        if counts is not None:
            objective = ctx.mk_and(objective, counts)
        portfolio = ctx.mk_portfolio(max_depth=depth)
        portfolio.add_target(objective)
        for net in [*a.inputs.values(), *b.inputs.values(), objective]:
            portfolio.add_watch(net)
        answer = portfolio.reach_targets(timeout=timeout)
        row = {"block": cond[0], "output": cond[1], "name": _net_name(nodes[cond[0]]),
               "engine": portfolio.get_last_engine(), "time": round(portfolio.get_last_time(), 3)}
        if answer == EngineResult.REACHABLE:
            trace = portfolio.get_last_trace()
            pair = [_test(diagram, copy, trace, (key, found), (tests, index)) for copy in (a, b)]
            row.update(status="covered", pair=pair)
        else:
            row["status"] = "unreachable" if answer == EngineResult.UNREACHABLE else "unknown"
        rows.append(row)
    result = {"decision": decision, "name": _net_name(nodes[decision]), "conditions": rows,
              "tests": tests, "covered": sum(r["status"] == "covered" for r in rows),
              "total": len(rows)}
    if start > 0:
        result["start"] = start
    return result


def _from_step(ctx, start):
    """A net true from step ``start`` on (a chain of latches, each false at
    the first step and then what the one before it was), or None for 0."""
    if start <= 0:
        return None
    boolean = ctx.mk_boolean_type()
    net = ctx.mk_true()
    for k in range(1, start + 1):
        latch = ctx.mk_latch(f"__mcdc_from{k}", boolean)
        ctx.set_latch_init_next(latch, ctx.mk_false(), net)
        net = latch
    return net


def _copy(diagram, ctx, name):
    """The diagram built in ``ctx`` under namespace ``name``."""
    ctx.push_namespace(name)
    circuit = build(diagram, ctx)
    ctx.pop_namespace()
    return circuit


def _objective(ctx, dec_a, dec_b, cond_a, cond_b):
    """The two copies differ in the condition and in the decision, and in each
    the decision would change with the condition (it is not masked)."""
    def decides(dec, cond):
        return ctx.mk_neq(ctx.mk_substitute(dec, ctx.mk_not(cond), cond), dec)
    return ctx.mk_and(ctx.mk_and(ctx.mk_neq(cond_a, cond_b), ctx.mk_neq(dec_a, dec_b)),
                      ctx.mk_and(decides(dec_a, cond_a), decides(dec_b, cond_b)))


def _test(diagram, copy, trace, what, table):
    """The test one copy runs in a trace, as an index in ``tests`` (the same
    run twice is one test): its inputs replayed on the diagram, its conditions
    and its decision at its last step. An input the trace leaves free (the
    objective holds whatever it is) takes false, or 0: a test is concrete."""
    key, found = what
    tests, index = table
    steps = trace.get_max_depth() + 1
    stimuli = _stimuli(copy, trace, steps)
    seen = json.dumps([steps, stimuli], sort_keys=True)
    if seen not in index:
        values = simulate(diagram, steps=steps, stimuli=stimuli)["values"]
        def last(k):
            return values.get(f"{k[0]}.{k[1]}", ["?"])[-1]
        index[seen] = len(tests)
        tests.append({"steps": steps, "stimuli": stimuli, "values": values,
                      "conditions": [last(c) for c in found], "decision": last(key)})
    return index[seen]


# --- sub-systems -----------------------------------------------------------------------

def _flatten(circuit):
    """A circuit with sub-systems as one flat netlist: each sub-system's blocks
    take its place, its In blocks become pass-throughs (``"via"``) of the wires
    into its inputs, its Out blocks pass-throughs of what drives them, and the
    wires out of it come from those. Returns the nodes, the edges and, for each
    sub-system output ``(id, index)``, the Out block it is."""
    nodes = {n["id"]: n for n in circuit.get("nodes", [])}
    subsystems = {nid for nid, n in nodes.items() if n["kind"] == "subsystem"}
    ports = {sid: {"input": [], "output": []} for sid in subsystems}
    for node in sorted(nodes.values(), key=lambda n: n["id"]):
        if node.get("parent") in subsystems and node["kind"] in ("input", "output"):
            ports[node["parent"]][node["kind"]].append(node)
    aliases = {(sid, index): out["id"]
               for sid in subsystems for index, out in enumerate(ports[sid]["output"])}
    edges = [_flat_edge(e, nodes, ports, aliases) for e in circuit.get("edges", [])]
    edges = [edge for edge in edges if edge is not None]
    flat = [_flat_node(node, nodes, subsystems) for node in nodes.values()
            if node["kind"] != "subsystem"]
    return flat, edges, aliases


def _flat_edge(edge, nodes, ports, aliases):
    """A wire of the flat netlist: from a sub-system, it leaves the Out block
    inside; into a sub-system, it enters the In block of its port's name."""
    if edge["from"] not in nodes or edge["to"] not in nodes:
        return None
    if edge["from"] in ports:
        key = (edge["from"], edge.get("fromPort", 0))
        if key not in aliases:
            raise DiagramError(f"{_label(nodes[edge['from']])} has no output {key[1]}")
        flat = {"from": aliases[key]}
    else:
        flat = {"from": edge["from"]}
        if "fromPort" in edge:
            flat["fromPort"] = edge["fromPort"]
    if edge["to"] in ports:
        into = [n for n in ports[edge["to"]]["input"] if n.get("name") == edge["port"]]
        if not into:
            raise DiagramError(f'{_label(nodes[edge["to"]])} has no input "{edge["port"]}"')
        return {**flat, "to": into[0]["id"], "port": "in"}
    return {**flat, "to": edge["to"], "port": edge["port"]}


def _flat_node(node, nodes, subsystems):
    """A block of the flat netlist: inside a sub-system, its name prefixed with
    the sub-system's, and an In or Out block a pass-through."""
    parent = node.get("parent")
    if parent is None:
        return node
    if parent not in subsystems:
        raise DiagramError(f"{_label(node)} is inside block {parent}, which is not a sub-system")
    copy = dict(node)
    if node.get("name"):
        copy["name"] = f"{_path(nodes, parent)}.{node['name']}"
    if node["kind"] in ("input", "output"):
        copy["kind"] = "via"
        copy["port_of"] = (_label(nodes[parent]), node["kind"], node.get("name"))
    return copy


def _path(nodes, sid):
    """The dotted names of the sub-systems down to ``sid``."""
    names = []
    while sid is not None:
        node = nodes[sid]
        names.append(node.get("name") or f"subsystem_{sid}")
        sid = node.get("parent")
    return ".".join(reversed(names))


def _netlist(diagram):
    """The flat netlist of a diagram: its blocks by id, the wire into each
    block's input (``into[id][port]``) and the sub-system outputs' Out blocks."""
    nodes, edges, aliases = _flatten(diagram.get("circuit") or {})
    into = {}
    for edge in edges:
        into.setdefault(edge["to"], {})[edge["port"]] = edge
    return {n["id"]: n for n in nodes}, into, aliases


def _gate_ports(node):
    op = node.get("op", "")
    if op == "ite":
        return ["if", "then", "else"]
    if op in _UNARY or op.startswith("cast_to_"):
        return ["in"]
    count = node.get("inputs", 2) if op in _VARIADIC else 2
    return [f"in{i}" for i in range(count)] if count > 2 else ["a", "b"]


# --- the builder ---------------------------------------------------------------------

class _Builder:  # pylint: disable=too-few-public-methods,too-many-instance-attributes

    def __init__(self, diagram, ctx):
        self.nodes, self.into, self.aliases = _netlist(diagram)
        self.ctx = ctx
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
        circuit.aliases = self.aliases
        circuit.input_types = {nid: self.nodes[nid].get("type", "bool") for nid in self.inputs}
        return circuit

    # -- what a block is ----------------------------------------------------------------

    def _ports(self, node):  # pylint: disable=too-many-return-statements
        kind = node["kind"]
        if kind == "latch":
            return ["init", "next"]
        if kind in ("output", "assertion", "target", "assumption", "via"):
            return ["in"]
        if kind == "component":
            return [pin["port"] for pin in self._spec(node)["inputs"]]
        if kind == "gate":
            return _gate_ports(node)
        return []

    def _deferred(self, node):
        """Inputs supplied after the block is built: they may be feedback."""
        if node["kind"] == "latch":
            return {"init", "next"}
        if node["kind"] == "component":
            return {pin["port"] for pin in self._spec(node)["inputs"] if pin["at"] == "setnext"}
        return set()

    def _spec(self, node):
        spec = catalogue.find(node.get("symbol"))
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

    def _input(self, node, port, optional=False):
        """The net wired into a block's input (None for an optional one unwired)."""
        edge = self.into.get(node["id"], {}).get(port)
        if edge is None:
            if optional:
                return None
            if node["kind"] == "via":
                where, kind, name = node["port_of"]
                if kind == "input":
                    raise DiagramError(f'{where}: input "{name}" is not wired')
                raise DiagramError(f'{where}: its output "{name}" is not connected inside')
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
        elif kind == "via":
            net = self._input(node, "in")
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
        args, kwargs = self._arguments(node, spec, spec["ctorArgs"])
        if spec.get("nameAsKeyword") and node.get("name"):
            kwargs["name"] = node["name"]
        result = call(*args, **kwargs)
        nid = node["id"]
        if spec["form"] == "class":
            self.objects[nid] = result
            for index, out in enumerate(spec["outputs"]):
                self.outputs[(nid, index)] = getattr(result, out["name"])
        elif len(spec["outputs"]) == 1:
            self.outputs[(nid, 0)] = result
        else:
            for index, net in enumerate(result):
                self.outputs[(nid, index)] = net

    def _arguments(self, node, spec, call):
        """The positional and keyword arguments of a library call; an optional
        input passed by keyword is left out while it is not wired."""
        optional = {pin["port"] for pin in spec["inputs"] if pin.get("optional")}
        args, kwargs = [], {}
        for arg in call:
            if arg.get("keyword"):
                net = self._input(node, arg["port"], optional=arg["port"] in optional)
                if net is not None:
                    kwargs[arg["keyword"]] = net
            else:
                args.append(self._argument(node, spec, arg))
        return args, kwargs

    def _argument(self, node, spec, arg):
        kind = arg["kind"]
        if kind == "ctx":
            return self.ctx
        if kind == "name":
            return node.get("name") or f"{node['symbol']}_{node['id']}"
        if kind == "input":
            return self._input(node, arg["port"])
        params = node.get("params") or {}
        default = next((p["default"] for p in spec["params"] if p["key"] == arg["key"]), None)
        value = params.get(arg["key"], default)
        if kind == "type":
            return self._type(value or "bool")
        return int(value if value is not None else 1)

    def _close(self, node):
        """Feedback and outputs, once every net exists."""
        kind = node["kind"]
        if kind == "latch":
            latch = self.outputs[(node["id"], 0)]
            self.ctx.set_latch_init_next(latch, self._input(node, "init"),
                                         self._input(node, "next"))
        elif kind == "component" and self._spec(node).get("setnextArgs"):
            spec = self._spec(node)
            args, kwargs = self._arguments(node, spec, spec["setnextArgs"])
            self.objects[node["id"]].set_init_next(*args, **kwargs)
        elif kind == "output":
            self.ctx.mk_output(self._input(node, "in"), node.get("name"))
        elif kind in ("assertion", "target"):
            self.properties.append((node, self._input(node, "in")))
        elif kind == "assumption":
            # every engine (and the portfolio's processes, through the recipe) keeps to it
            self.ctx.push_assumption(self._input(node, "in"))
        if node.get("output") and kind not in ("output", "via"):
            self.ctx.mk_output(self.outputs[(node["id"], 0)], node.get("name"))


def _primary(node):
    if node.get("kind") == "component":
        spec = catalogue.find(node.get("symbol"))
        return spec["primary"] if spec else 0
    return 0


def _label(node):
    kind = node.get("kind")
    what = node.get("op") if kind == "gate" else node.get("symbol") if kind == "component" else kind
    name = node.get("name")
    return f'{what} "{name}"' if name else f"{what} {node.get('id')}"


# --- command line ------------------------------------------------------------------------

def main(argv=None):
    """``python -m intrepyd.diagram simulate|verify|mcdc FILE|- [options]``, or ``catalogue``"""
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
    ver.add_argument("--certificates", action="store_true", default=None,
                     help="give each proved property its proof certificate, as SMT-LIB 2")
    gen = sub.add_parser("mcdc", help="generate MC/DC tests for the diagram's decisions, "
                                      "print JSON")
    gen.add_argument("diagram", help="a *.intrepyd.json file, or - for standard input")
    gen.add_argument("--decision", type=int, action="append",
                     help="a decision's block id (repeat for several; default: the diagram's)")
    gen.add_argument("--depth", type=int,
                     help="the longest test, in steps after the first (default: 20)")
    gen.add_argument("--timeout", type=float, help="seconds per condition (default: 30)")
    sub.add_parser("catalogue", help="print the library blocks a diagram may use, as JSON")
    args = parser.parse_args(argv)
    if args.command == "catalogue":
        sys.stdout.write(json.dumps(catalogue.catalogue()) + "\n")
        return 0
    try:
        diagram = load(sys.stdin if args.diagram == "-" else args.diagram)
        if args.command == "verify":
            result = verify(diagram, engine=args.engine, timeout=args.timeout, depth=args.depth,
                            certificates=args.certificates)
        elif args.command == "mcdc":
            result = mcdc(diagram, decisions=args.decision, depth=args.depth, timeout=args.timeout)
        else:
            result = simulate(diagram, steps=args.steps)
    except Exception as err:  # pylint: disable=broad-except  # reported, not raised, to the editor
        sys.stderr.write(f"{type(err).__name__}: {err}\n")
        return 1
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
