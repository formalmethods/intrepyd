# Performance against Kind2

How intrepyd compares to [Kind2](https://kind2-mc.github.io/kind2/), the
reference model checker for Lustre, on the Kind2 benchmark set, with a **30
second timeout**. The comparison is run with the benchmark harness
(`benchmarks/harness.py`); this page describes the method and the two plots it
produces, and gives the exact commands so the numbers can be regenerated.

## Method

- **Same machine, same budget.** Every tool runs on the same machine, each run
  in its own process, with a 30 s timeout and a memory cap, and each tool gets
  the same number of cores — a single engine one core, a portfolio (intrepyd's
  or Kind2's) the same `--portfolio-cpus`.
- **Same semantics.** Kind2 reads Lustre `int` as unbounded integers, so the
  comparison uses `--int-type int`; the 32-bit encoding (`int32`) is reported
  apart. Only benchmarks on which the two tools **agree** on the verdict are
  compared for speed; disagreements are bugs and are reported separately.
- **What is compared.** intrepyd's portfolio against Kind2's default portfolio,
  and engine by engine (BMC, k-induction, IC3) against the matching Kind2
  engine.

## The two plots

- **Scatter plot** — one point per benchmark, Kind2's time on the x axis and
  intrepyd's on the y axis, log-log, with the timeout as the border. A point
  below the diagonal is a benchmark intrepyd solves faster; a point on a border
  line is one that only one tool solved within the budget.
- **Benchmarks solved over time** (a cactus plot) — the number of benchmarks
  solved against cumulative time, one curve per tool. A curve that reaches
  higher solves more within the budget; a curve further left is faster.

## Regenerating the numbers

```bash
# 1. Run both tools on the benchmarks with a 30 s timeout (needs Kind2 and the
#    z3 it uses; this takes a while)
python benchmarks/harness.py run results-int.jsonl \
    --tools portfolio,bmc,kind,pdr,kind2,kind2_bmc,kind2_kind,kind2_ic3 \
    --int-type int --timeout 30 --kind2 /path/to/kind2 --z3 /path/to/z3

# 2. Check the two tools agree where they both answer
python benchmarks/harness.py report results-int.jsonl --expected benchmarks/kind2-benchmarks.txt

# 3. Produce the plots
python benchmarks/harness.py plot results-int.jsonl \
    --pair portfolio,kind2 --out-dir docs/assets/benchmarks
```

Step 3 writes `scatter.png` and `cactus.png`. The run is machine-dependent, so
the published plots are produced on the reference benchmarking machine and
committed under `docs/assets/benchmarks/`; drop them in and reference them here
once generated.

See also the [benchmarking guide](benchmarking.md) for running a single
benchmark, and [model checking](model-checking.md) for the engines themselves.
