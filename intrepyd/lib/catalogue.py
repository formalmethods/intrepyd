"""
The catalogue of :mod:`intrepyd.lib`: every library block described as data —
what it is called, its parameters, its input pins and their types, its outputs
and their types, and how to call it. It is what a tool needs to offer the
blocks without reading their code: the intrepid-vscode circuit editor builds
its palette from it (``python -m intrepyd.diagram catalogue`` prints it as
JSON), and :mod:`intrepyd.diagram` builds the blocks of a diagram with it.

A block (one entry of ``BLOCKS``) has:

- ``module`` (``"eda"`` or ``"plc"``), ``symbol`` (the name in that module),
  ``form`` (``"func"``: a function returning its outputs; ``"class"``: built,
  then closed with ``set_init_next``), ``category``, ``label`` and
  ``description``;
- ``params``: the scalar parameters, each ``{"key", "kind", "label",
  "default"}`` with ``kind`` ``"type"`` (a type name: ``bool``, ``int8``, ...)
  or ``"int"`` (an integer);
- ``inputs``: the input pins in order, each ``{"port", "at", "type"}`` (a
  ``null`` type takes any), where
  ``at`` is ``"ctor"`` (needed to build the block) or ``"setnext"`` (given to
  ``set_init_next``, so it may come from the block's own output), and an
  ``"optional": true`` pin may stay unwired (the block's default is used);
- ``outputs``: the outputs in order, each ``{"name", "type"}``, and
  ``primary``, the index of the output a wire carries when it does not say;
- ``ctorArgs`` and ``setnextArgs``: the arguments of the call, each one of
  ``{"kind": "ctx"}``, ``{"kind": "name"}`` (the instance name),
  ``{"kind": "input", "port"}`` (the net wired to that pin; with
  ``"keyword"``, passed by that keyword and only when wired),
  ``{"kind": "type", "key"}`` and ``{"kind": "int", "key"}`` (a parameter);
  ``nameAsKeyword`` passes the name as ``name=...`` instead.

A type is ``{"kind": "bool"}``, ``{"kind": "param", "key"}`` (the type a
parameter names) or ``{"kind": "like", "port"}`` (the type of another input).
"""

FORMAT = "intrepyd-catalogue"
VERSION = 1

_CTX = {"kind": "ctx"}
_NAME = {"kind": "name"}
_BOOL = {"kind": "bool"}


def _param(key):
    return {"kind": "param", "key": key}


def _like(port):
    return {"kind": "like", "port": port}


def _arg(port, keyword=None):
    arg = {"kind": "input", "port": port}
    if keyword:
        arg["keyword"] = keyword
    return arg


def _type(key):
    return {"kind": "type", "key": key}


def _int(key):
    return {"kind": "int", "key": key}


def _pin(port, type_, at="ctor", optional=False):
    pin = {"port": port, "at": at, "type": type_}
    if optional:
        pin["optional"] = True
    return pin


def _out(name, type_):
    return {"name": name, "type": type_}


def _type_param(key="t", default="bool"):
    return {"key": key, "kind": "type", "label": "type", "default": default}


# pylint: disable=line-too-long
_T = _param("t")
_TYP = _param("typ")

BLOCKS = [
    # --- EDA ---------------------------------------------------------------
    {"module": "eda", "symbol": "mk_mux", "form": "func", "category": "EDA",
     "label": "MUX 2:1", "description": "2:1 multiplexer: out = in1 if sel else in0.",
     "params": [],
     "inputs": [_pin("sel", _BOOL), _pin("in0", None), _pin("in1", _like("in0"))],
     "outputs": [_out("out", _like("in0"))], "primary": 0,
     "ctorArgs": [_CTX, _arg("sel"), _arg("in0"), _arg("in1")], "nameAsKeyword": True},
    {"module": "eda", "symbol": "mk_clock", "form": "func", "category": "EDA",
     "label": "Clock", "description": "A clock signal, and the free input that drives its first cycle.",
     "params": [], "inputs": [],
     "outputs": [_out("clk", _BOOL), _out("in", _BOOL)], "primary": 0,
     "ctorArgs": [_CTX, _NAME]},
    {"module": "eda", "symbol": "mk_counter", "form": "func", "category": "EDA",
     "label": "Counter",
     "description": "Counts from init by increment while enable holds, up to limit; reset brings it back to init. Outputs the count and whether it reached the limit.",
     "params": [_type_param("t", "int8")],
     "inputs": [_pin("limit", _T), _pin("init", _T, optional=True), _pin("increment", _T, optional=True),
                _pin("enable", _BOOL, optional=True), _pin("reset", _BOOL, optional=True)],
     "outputs": [_out("counter", _T), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _type("t"), _arg("limit"), _arg("init", "init"),
                  _arg("increment", "increment"), _arg("enable", "enable"), _arg("reset", "reset")]},
    {"module": "eda", "symbol": "LatchD", "form": "class", "category": "EDA",
     "label": "Latch D (LD)", "description": "A data latch with enable: Q holds D when E is true.",
     "params": [_type_param()],
     "inputs": [_pin("init", _T, "setnext"), _pin("d", _T, "setnext"), _pin("e", _BOOL, "setnext")],
     "outputs": [_out("q", _T)], "primary": 0,
     "ctorArgs": [_CTX, _NAME, _type("t")], "setnextArgs": [_arg("init"), _arg("d"), _arg("e")]},
    {"module": "eda", "symbol": "Delay", "form": "class", "category": "EDA",
     "label": "Delay", "description": "Delays a signal by one full clock cycle.",
     "params": [_type_param()],
     "inputs": [_pin("init", _T, "setnext"), _pin("d", _T, "setnext")],
     "outputs": [_out("q", _T)], "primary": 0,
     "ctorArgs": [_CTX, _NAME, _type("t")], "setnextArgs": [_arg("init"), _arg("d")]},
    {"module": "eda", "symbol": "FlipFlopD", "form": "class", "category": "EDA",
     "label": "Flip-flop D (FFD)", "description": "A D flip-flop clocked by C.",
     "params": [_type_param()],
     "inputs": [_pin("c", _BOOL), _pin("init", _T, "setnext"), _pin("d", _T, "setnext")],
     "outputs": [_out("q", _T)], "primary": 0,
     "ctorArgs": [_CTX, _NAME, _type("t"), _arg("c")], "setnextArgs": [_arg("init"), _arg("d")]},
    {"module": "eda", "symbol": "FlipFlopDE", "form": "class", "category": "EDA",
     "label": "Flip-flop D+E (FFDE)", "description": "A D flip-flop with enable, clocked by C.",
     "params": [_type_param()],
     "inputs": [_pin("c", _BOOL), _pin("init", _T, "setnext"), _pin("d", _T, "setnext"),
                _pin("e", _BOOL, "setnext")],
     "outputs": [_out("q", _T)], "primary": 0,
     "ctorArgs": [_CTX, _NAME, _type("t"), _arg("c")], "setnextArgs": [_arg("init"), _arg("d"), _arg("e")]},
    {"module": "eda", "symbol": "ShiftRegister", "form": "class", "category": "EDA",
     "label": "Shift register", "description": "D delayed by `length` cycles.",
     "params": [_type_param(), {"key": "length", "kind": "int", "label": "length", "default": "3"}],
     "inputs": [_pin("init", _T, "setnext"), _pin("d", _T, "setnext")],
     "outputs": [_out("q", _T)], "primary": 0,
     "ctorArgs": [_CTX, _NAME, _type("t"), _int("length")], "setnextArgs": [_arg("init"), _arg("d")]},
    # --- PLC (IEC 61131-3) -------------------------------------------------
    {"module": "plc", "symbol": "mk_r_trig", "form": "func", "category": "PLC",
     "label": "R_TRIG", "description": "Rising-edge detector on clk.",
     "params": [], "inputs": [_pin("clk", _BOOL)], "outputs": [_out("Q", _BOOL)], "primary": 0,
     "ctorArgs": [_CTX, _arg("clk"), _NAME]},
    {"module": "plc", "symbol": "mk_f_trig", "form": "func", "category": "PLC",
     "label": "F_TRIG", "description": "Falling-edge detector on clk.",
     "params": [], "inputs": [_pin("clk", _BOOL)], "outputs": [_out("Q", _BOOL)], "primary": 0,
     "ctorArgs": [_CTX, _arg("clk"), _NAME]},
    {"module": "plc", "symbol": "mk_sr", "form": "func", "category": "PLC",
     "label": "SR bistable", "description": "Set-dominant bistable latch.",
     "params": [], "inputs": [_pin("s", _BOOL), _pin("r", _BOOL)], "outputs": [_out("Q", _BOOL)], "primary": 0,
     "ctorArgs": [_CTX, _arg("s"), _arg("r"), _NAME]},
    {"module": "plc", "symbol": "mk_rs", "form": "func", "category": "PLC",
     "label": "RS bistable", "description": "Reset-dominant bistable latch.",
     "params": [], "inputs": [_pin("s", _BOOL), _pin("r", _BOOL)], "outputs": [_out("Q", _BOOL)], "primary": 0,
     "ctorArgs": [_CTX, _arg("s"), _arg("r"), _NAME]},
    {"module": "plc", "symbol": "mk_ctu", "form": "func", "category": "PLC",
     "label": "CTU (up counter)", "description": "Counts up on cu's rising edge, saturates at pv.",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("cu", _BOOL), _pin("reset", _BOOL), _pin("pv", _TYP)],
     "outputs": [_out("CV", _TYP), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("cu"), _arg("reset"), _arg("pv"), _type("typ")]},
    {"module": "plc", "symbol": "mk_ctd", "form": "func", "category": "PLC",
     "label": "CTD (down counter)", "description": "Counts down on cd's rising edge from the preset.",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("cd", _BOOL), _pin("load", _BOOL), _pin("pv", _TYP)],
     "outputs": [_out("CV", _TYP), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("cd"), _arg("load"), _arg("pv"), _type("typ")]},
    {"module": "plc", "symbol": "mk_ctud", "form": "func", "category": "PLC",
     "label": "CTUD (up/down counter)", "description": "Combined up/down counter.",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("cu", _BOOL), _pin("cd", _BOOL), _pin("reset", _BOOL), _pin("load", _BOOL),
                _pin("pv", _TYP)],
     "outputs": [_out("CV", _TYP), _out("QU", _BOOL), _out("QD", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("cu"), _arg("cd"), _arg("reset"), _arg("load"), _arg("pv"), _type("typ")]},
    {"module": "plc", "symbol": "mk_ton", "form": "func", "category": "PLC",
     "label": "TON (on-delay)", "description": "On-delay timer (preset pt in cycles).",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("in", _BOOL), _pin("pt", _TYP)],
     "outputs": [_out("ET", _TYP), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("in"), _arg("pt"), _type("typ")]},
    {"module": "plc", "symbol": "mk_tof", "form": "func", "category": "PLC",
     "label": "TOF (off-delay)", "description": "Off-delay timer (preset pt in cycles).",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("in", _BOOL), _pin("pt", _TYP)],
     "outputs": [_out("ET", _TYP), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("in"), _arg("pt"), _type("typ")]},
    {"module": "plc", "symbol": "mk_tp", "form": "func", "category": "PLC",
     "label": "TP (pulse)", "description": "Pulse timer (preset pt in cycles).",
     "params": [_type_param("typ", "int8")],
     "inputs": [_pin("in", _BOOL), _pin("pt", _TYP)],
     "outputs": [_out("ET", _TYP), _out("Q", _BOOL)], "primary": 1,
     "ctorArgs": [_CTX, _NAME, _arg("in"), _arg("pt"), _type("typ")]},
]
# pylint: enable=line-too-long

_BY_SYMBOL = {block["symbol"]: block for block in BLOCKS}


def find(symbol):
    """The block called ``symbol``, or None."""
    return _BY_SYMBOL.get(symbol)


def catalogue():
    """The catalogue as one JSON-ready document."""
    return {"format": FORMAT, "version": VERSION, "blocks": BLOCKS}
