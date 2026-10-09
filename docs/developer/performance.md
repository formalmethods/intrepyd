# Measuring performance

## The benchmark harness

Performance work is driven by the benchmark harness in `benchmarks/`, which
runs the whole Kind2 Lustre suite with intrepyd's engines and with Kind2
itself, and compares the runs. The [user guide covers how to run
it](../guide/benchmarking.md); for development, the points that matter are:

- `benchmarks/harness.py run OUT.jsonl` appends one JSON line per
  file × tool pair, and skips the pairs a previous run already has, so a run
  can be resumed and several runs merged;
- `--library PATH` chooses which `libintrepid` to load, so you can run the
  same suite against two builds and compare them;
- `benchmarks/harness.py compare A.jsonl B.jsonl` reports, per tool, the
  models one build solves that the other does not, and those one solves at
  least twice as fast — the regression check for a change to the engines or
  the encoding.

Measure before and after a change, on the same machine with the same timeout,
and keep the two `.jsonl` files. The Kind2 runs need not be repeated for a new
intrepid build: `report` merges runs and keeps the Kind2 columns.

## Profiling without root

`perf` is restricted on most machines (`kernel.perf_event_paranoid`), and this
project does not assume root. Profile in user space instead:

- **python side:** `python -m cProfile -o out.prof script.py`, read with
  `pstats` or `snakeviz`. This shows where time goes in intrepyd, but attributes
  everything inside a `ctypes` call to the library as a single cost.
- **C++ side:** build intrepid in debug or with frame pointers and use a
  sampling profiler that needs no root (for example `py-spy --native`, which
  samples both the python and the native stacks), or the timing the engines
  and the harness already report. The intrepid developer guide has more on
  profiling the library.

For a single model, the harness's per-run time and the engine that answered
(for a portfolio) are usually enough to tell a regression from noise without a
profiler at all.
