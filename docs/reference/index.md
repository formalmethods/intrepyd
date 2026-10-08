# API reference

The reference is generated from the source code and its docstrings, so it
always matches the installed version. It covers the public API; the internal
modules (the `ctypes` binding in `intrepyd.api`, the ANTLR-generated Lustre and
IEC 61131-3 front-ends, and other helpers) are left out.

| Module | What it is |
| ------ | ---------- |
| [Context](context.md) | The factory for types, nets, engines and traces |
| [Engines](engine.md) | BMC, k-induction, backward reachability and IC3/PDR |
| [Portfolio](portfolio.md) | Runs the engines in parallel |
| [Circuit](circuit.md) | Base class for translated and hand-built models |
| [Trace](trace.md) | Input and watched values over time |
| [Simulator](simulator.md) | Propagates a trace through a circuit |
| [Tools](tools.md) | `translate_*` front-ends and `simulate` |
| [Parser](parser.md) | Reads Intrepid's line-based syntax |
| [Simulink](simulink.md) | Binding of the Simulink front-end library |
| [Remote](remote.md) | Using an intrepid-server from python |
| [Helpers](helpers.md) | SCR, pseudo-boolean and plotting helpers |
