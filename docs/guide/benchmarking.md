# Benchmarking

## A single benchmark

`benchmarks/run_one.py` runs a single Lustre benchmark under one engine, in a
separate process, with a timeout:

```bash
python benchmarks/run_one.py <file.lus> <tool> [-t SECONDS] [--int-type int32|int]
```

`<tool>` is `br` (backward reachability), `bmc`, `bmc_ti` (BMC with
k-induction), `pdr`, or `portfolio` (all of them in parallel); the default
timeout is 60 seconds. It prints the verdict — `Valid`, `Invalid`, `Unknown`,
`Timeout` or `Exception` — and the elapsed time, followed, for `portfolio`, by
the engine that gave the verdict. The benchmark expects the top node to be
called `top` and to expose an `OK` output, which is the Kind2 convention.

```console
$ python benchmarks/run_one.py intrepyd/tests/lustre/peterson_1.lus br -t 30
intrepyd/tests/lustre/peterson_1.lus br Valid 0.018

$ python benchmarks/run_one.py intrepyd/tests/lustre/peterson_1.lus bmc -t 5
intrepyd/tests/lustre/peterson_1.lus bmc Timeout 5
```

Plain `bmc` times out here because bounded model checking cannot prove a
property, only refute it — which is what `bmc_ti` adds.

The driver translates into an `encoding.py` in the current directory and runs
the engine in a child process, so run it from a scratch directory, with the
python of a virtualenv where intrepyd is installed, such as the editable one of
`make install_dev`.

## The whole suite, and Kind2

`benchmarks/harness.py` runs the whole Kind2 benchmark suite listed in
`benchmarks/kind2-benchmarks.txt`, with intrepyd's engines and with
[Kind2](https://github.com/kind2-mc/kind2) itself, and reports and compares the
runs:

```bash
python benchmarks/harness.py run OUT.jsonl [--tools bmc,kind,br,pdr,portfolio]
    [--timeout 10] [--memory 4096] [--int-type int32|int] [--library PATH]
    [--cpus 0-15] [--portfolio-cpus 4] [--filter REGEX]
python benchmarks/harness.py report OUT.jsonl... [--expected benchmarks/kind2-benchmarks.txt]
python benchmarks/harness.py compare A.jsonl B.jsonl
```

- `run` runs each file × tool pair in a process of its own, as many at a time
  as there are cpus (by default one thread per physical core): a single engine
  is bound to one cpu, a portfolio to `--portfolio-cpus`, and a run is killed
  past its timeout or its memory limit. Results are appended to `OUT.jsonl` one
  line each, and a run started again skips the pairs it has. Each file is
  translated once per `--int-type` into `benchmarks/cache`; `--library` chooses
  the `libintrepid` to load, to compare two builds.
- The tools are intrepyd's `bmc`, `kind` (k-induction), `br`, `pdr` and
  `portfolio`, and Kind2's `kind2` (its default portfolio), `kind2_bmc`,
  `kind2_kind`, `kind2_ic3` and `kind2_ic3ia`. The Kind2 tools need the `kind2`
  executable (`--kind2` or `$KIND2`) and a z3 executable for it (`--z3` or
  `$KIND2_Z3`), at best the version that intrepid is built with. Kind2 reads
  Lustre `int` as unbounded integers, so compare it with `--int-type int`.
- `report` gives, per tool, the models solved, the verdicts and the times; the
  models where two tools disagree; the verdicts that contradict `--expected`
  (whose verdicts follow 32-bit semantics); which engine answered for each
  portfolio; and each intrepyd tool against its Kind2 counterpart: the models
  solved by one only, and those solved at least twice as fast by one. Given
  several runs, it merges them, the later one winning, so that the Kind2 tools
  need not run again for a new build of intrepid. `compare` does the same for
  each tool of two runs.

Results of a 5-second-timeout run of 2021 are kept in
`benchmarks/results_5_seconds/`.
