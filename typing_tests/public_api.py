"""Static consumer checks, run by mypy without importing the native library.

The intentional errors must remain errors: warn_unused_ignores catches APIs
that silently lose their annotations and fall back to accepting Any.
"""

from collections.abc import Iterable
from types import ModuleType
from typing import Literal, assert_type

from intrepyd import Context
from intrepyd.api import Net
from intrepyd.circuit import Circuit
from intrepyd.engine import EngineResult
from intrepyd.lib import eda, plc
from intrepyd.pseudoboolean import mk_exactly_one
from intrepyd.tools import translate_lustre
from intrepyd.trace import Trace

ctx = Context()
signal = ctx.mk_input("signal", ctx.booleantype)
trace = ctx.mk_trace()
assert_type(trace, Trace)
assert_type(trace.get_value(signal, 0), str)
assert_type(trace.get_max_depth(), int)
assert_type(trace.get_as_net_dictionary(), dict[Net, list[str]])
assert_type(trace.get_as_net_dictionary(ctx.net2name), dict[str, list[str]])
assert_type(trace.get_as_net_dictionary({signal: 1}), dict[int, list[str]])
assert_type(trace.get_as_depth_dictionary(), dict[int, list[str]])
assert_type(Trace.get_numeric_value("?"), int | float | Literal["?"])
trace.set_value(signal, 0, "true")
trace.set_value(signal, 0, True)  # type: ignore[arg-type]
ctx.mk_simulator().simulate(trace, 2)
ctx.mk_simulator().add_watch(ctx.booleantype)  # type: ignore[arg-type]

bmc = ctx.mk_bmc()
assert_type(bmc.reach_targets(), EngineResult)
assert_type(bmc.get_last_trace(), Trace)
assert_type(bmc.get_last_reached_targets(), Iterable[Net])
assert_type(bmc.get_last_certificate(), str | None)
bmc.add_target(ctx.booleantype)  # type: ignore[arg-type]
bmc.set_current_depth("2")  # type: ignore[arg-type]
portfolio = ctx.mk_portfolio()
assert_type(portfolio.reach_targets(timeout=1.5), EngineResult)
assert_type(portfolio.get_last_engine(), str | None)
assert_type(portfolio.get_last_time(), float | None)
assert_type(portfolio.get_last_errors(), dict[str, str])
assert_type(portfolio.get_last_reached_targets(), tuple[Net, ...])
assert_type(portfolio.get_last_trace(), Trace)
portfolio.add_target(ctx.booleantype)  # type: ignore[arg-type]

model = Circuit(ctx, "model")
assert_type(model.inputs, dict[str, Net])
assert_type(model.mk_naked_circuit({"in": signal}), dict[str, Net])
model.mk_naked_circuit({"in": ctx.booleantype})  # type: ignore[dict-item]
assert_type(eda.mk_clock(ctx, "clock"), tuple[Net, Net])
assert_type(eda.Delay(ctx, "delay", ctx.booleantype).q, Net)
assert_type(plc.mk_r_trig(ctx, signal, "edge"), Net)
assert_type(plc.mk_ton(ctx, "timer", signal, ctx.mk_number("3", ctx.inttype), ctx.inttype),
            tuple[Net, Net])
assert_type(mk_exactly_one(ctx, [signal], "one"), Net)
eda.mk_mux(ctx, ctx.booleantype, signal, signal)  # type: ignore[arg-type]
assert_type(translate_lustre("model.lus", "top", "real"), ModuleType)
