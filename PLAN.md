# Plan

What we have decided to implement, or would like to implement, in intrepyd
and in intrepid. Each item says what and why; once an item is done, it moves
to the bottom with a reference to its commit.

Items are numbered, so they can be referred to as #1, #2, and so on. A number
belongs to its item for good: new items take the next free number, and an item
keeps its number when it is done or dropped.

## To do

### #1 Benchmark harness for the Lustre models in `benchmarks/`

A tool to measure the engines on the Kind2 benchmarks, for the next rounds of
optimization:

- translates each `.lus` file once, and keeps the encodings in a cache;
- runs each file × engine pair (`bmc`, `bmc_ti`, `br`) in a separate process,
  in parallel, with a timeout and a memory limit;
- chooses which `libintrepid` to load, to compare two versions with
  everything else equal, and how integers are encoded (`int32` or `int`);
- reports, per engine, verdicts, solved instances and time, flags verdicts
  that contradict `kind2-benchmarks.txt`, and compares two runs instance by
  instance.

A first version was written while optimizing BMC and backward reachability,
but in a temporary directory: it needs writing again here, replacing
`run_one.py` and `kind2_benchmarks.py` or next to them.

Note: the verdicts in `kind2-benchmarks.txt` follow 32 bit semantics; with
`--int-type int`, some 15 to 18 instances (`ticket3i_*`, `durationThm_*`)
rightly get a different verdict.

### #2 IC3/PDR engine

What remains unsolved on the benchmarks is mostly properties that need
invariants: deep chains, with one state per level, that neither k-induction
nor backward reachability can close. The natural next step is an IC3/PDR
engine. z3 includes one, Spacer, available through its API for Constrained
Horn Clauses: the system is described as

    Inv(s)  <-  Init(s)
    Inv(s') <-  Inv(s) /\ Trans(s, i, s')
    false   <-  Inv(s) /\ Bad(s, i)

and Spacer finds an inductive invariant, or a counterexample. It works well on
linear arithmetic, so mostly with `inttype='int'`; it is weaker on
bit-vectors.

### #3 Rewrite the documentation in `docs/`

`docs/` is hard to use: it is the output of pdoc3 (`make build_docs`), one
page per module listing its classes and methods, with no explanation of how
they fit together. It also has pages for internals no user needs, such as the
ANTLR generated parsers and visitors of `lustre2py`, `iec611312py` and
`formula2py`, and it is out of date: `api.md` still describes the SWIG module
that the ctypes binding replaced.

Rewrite it for people who use intrepyd or develop it:

- a guide that goes from concepts to tasks: contexts, types and nets,
  circuits, latches and assumptions, traces, then simulating, model checking
  with each engine (what it can prove, how to read its results, when to pick
  it), and importing Lustre and IEC 61131-3 models, including the int
  encoding choice;
- the REST service, documented here too rather than only on Postman;
- an API reference that is curated rather than dumped: the public classes
  and functions, with examples, and without the generated internals.

The README keeps the short tour and points to `docs/` for the rest. This is
documentation for users only: everything about developing intrepyd moves to
the developer documentation of #4.

### #4 Developer documentation, kept apart from the user documentation

Nothing explains how to work on the code: how to debug a failure, how the
pieces fit together, how to measure a change. What little there is sits in
the README, mixed with the user documentation (the Development section, the
build and release targets, the troubleshooting of builds).

Write a developer documentation, separate from the user one of #3, covering:

- architecture: how intrepyd, intrepid and intrepid-dependencies relate; in
  intrepid, the net stores, circuits, unroller, solvers and engines, and how
  BMC, k-induction and backward reachability work;
- debugging: building intrepid in debug mode and loading it from intrepyd
  through `INTREPID_DIR` or `INTREPID_LIBRARY`; running python under gdb;
  the API trace (the `trace.cpp` the library writes on errors, and
  `apitrace_dump_to_file`) and how to replay it as a C++ program; engine
  verbosity; checking an engine result against another engine or the
  simulator;
- testing: the C++ and python suites, what each covers, how to add a test;
- measuring performance: the benchmark harness of #1, and profiling without
  root (perf is restricted on most machines);
- the release process of each repository, in order: intrepid-dependencies,
  intrepid, intrepyd, with the checksums and versions to update.

intrepid and intrepid-dependencies are separate repositories, and intrepid is
private: what only concerns their internals belongs in their own
documentation, and the intrepyd developer documentation links to it.

### #5 Move the REST service and the Docker image to their own repository

intrepyd also carries a web service: the Flask blueprints in `app/` and their
tests, `intrepid.py`, `start_development_server.sh`, and the Docker image
(`Dockerfile`, `Makefile.docker`, `docker/`, `.dockerignore`). Because of it,
`flask` and `gunicorn` are install requirements of intrepyd, so everyone who
installs the library gets a web server too, and the repository mixes two
products with different users and release cycles.

Create a new repository for the service and its image, which depends on
intrepyd as a package (a pinned version from PyPI, or a local checkout during
development). intrepyd then stays a standalone project, focused on the python
library: no Flask code, no Docker files, and no web dependencies.

To settle along the way: the name of the new repository; where the REST API
documentation lives (with the service, linked from #3); and how its CI gets
intrepyd and the intrepid library.

### #6 Review how the python library is packaged and released

The packaging grew by accretion and should be reviewed as a whole:

- the build is described by `setup.py` and a `setup.cfg` with a deprecated
  key, with no `pyproject.toml`; setuptools warns about the license
  classifiers, and the license metadata has to say that the bundled intrepid
  library is under its own license;
- dependencies are duplicated between `setup.py` and `requirements.txt`, and
  development tools (pylint, build) are mixed with runtime ones; `flask` and
  `gunicorn` go away with #5;
- the wheels, one per platform, are built by hand on one machine with
  `make wheels` and uploaded by hand with twine: building and publishing
  them should happen in CI, on a tag, as the intrepid releases do;
- `VERSION` and `INTREPID_VERSION` are bumped by hand: decide how versions are
  numbered and checked, and add a `make release` like the other repositories;
- the published PyPI releases still ship the old SWIG `_api.so`, built for
  python 3.9 only, with macOS wheels that will no longer be produced; decide
  what the first release of the new layout is called and what it says about
  the change.

### #7 Benchmark against Kind2 on the Lustre models, and optimize where we lose

Measure intrepyd against Kind2, the reference model checker for Lustre, on the
Kind2 benchmarks in `benchmarks/`, and where Kind2 does better (it solves
models we do not, or solves them much faster) find out why and improve our
engines.

For the comparison to be fair:

- same machine, same timeout, same models, each tool given the same number of
  cores; Kind2 runs a portfolio of engines in parallel by default, so compare
  it both as a portfolio and engine by engine (BMC, k-induction, IC3) against
  ours;
- same semantics: Kind2 treats Lustre `int` as unbounded integers, so
  intrepyd runs with `inttype='int'`, and the 32 bit encoding is reported
  apart;
- check that both tools agree on every verdict they both give: a
  disagreement is a bug in one of them, to be understood before any timing.

This builds on the benchmark harness of #1, which should learn to run Kind2
too. The losses then drive the optimization work: profile them, as was done
for BMC and backward reachability, and fix what they show. Many will need
invariants, which is #2.

To settle: which Kind2 release, and which SMT solver it uses (z3, cvc5, or
both), installed how; and whether `kind2-benchmarks.txt` comes from Kind2 at
all, since its verdicts follow 32 bit semantics.
