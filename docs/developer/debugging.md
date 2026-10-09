# Debugging

## Running against a local build of intrepid

By default intrepyd loads the released library that `make fetch_intrepid`
puts in `intrepyd/`. To debug a problem that reaches into the C++ library,
build intrepid yourself — in debug mode, with its assertions on — and load
that build instead:

```bash
make -C ../intrepid debug
make fetch_intrepid INTREPID_DIR=../intrepid/build_debug
```

`INTREPID_DIR` takes a build directory, a release archive or an extracted one.
At run time, the `INTREPID_LIBRARY` environment variable overrides everything:
set it to the path of a library file and `intrepyd.api` loads that one, which
is handy for pointing a single test at a particular build:

```bash
INTREPID_LIBRARY=../intrepid/build_debug/libintrepid.so python -m pytest ...
```

A debug build turns the library's internal checks into assertions that abort
with a message and a stack, instead of the silent wrong answer a release build
might give.

## Under gdb

Because the heavy lifting is in the C++ library, debug python under gdb to see
both sides of the `ctypes` boundary:

```bash
gdb --args python my_script.py
(gdb) run
(gdb) bt         # once it stops on the abort or the fault
```

A debug build of the library gives readable frames and line numbers on the
C++ side.

## The API trace

On an error, the library writes the API calls made so far to `trace.cpp` in
the current directory, as a self-contained C++ program that replays them. It
is the fastest way to hand a failure to whoever works on intrepid: it
reproduces the problem without python, intrepyd or the model in between.
`intrepyd.api` also exposes the calls that produce it on demand:

```python
import intrepyd.api as api
api.apitrace_dump_to_file('trace.cpp')   # or
api.apitrace_print_to_stdout()
api.apitrace_print_to_stderr()
```

Compile and run the trace against a build of intrepid to reproduce the issue
there; the intrepid developer guide (in the intrepid repository) says how.
`trace.cpp` is a debugging aid, and safe to delete.

## Cross-checking a result

A verdict is only as trustworthy as the engine that gave it, so check one
engine against another, and against the simulator:

- a `REACHABLE` answer comes with a counterexample trace. Replay it with the
  [simulator](../guide/simulating.md) (`get_as_dataframe`, feed the inputs
  back) and confirm the target is really reached; this is what
  `test_eq_check.py` and the value tests do.
- run the same target under a second engine. BMC and PDR should agree on a
  reachable target; k-induction, backward reachability and PDR should agree on
  an unreachable one. A disagreement is a bug — in the model or in an engine.
- PDR and backward reachability **check their own proofs** before answering
  `UNREACHABLE`: if the invariant does not hold, the answer is `UNKNOWN`, not a
  wrong proof. An `UNKNOWN` where a proof was expected is worth investigating.

The [benchmark harness](../guide/benchmarking.md) automates the cross-check
across the whole Kind2 suite: its `report` command lists the models where two
tools disagree, and the verdicts that contradict the expected ones.
