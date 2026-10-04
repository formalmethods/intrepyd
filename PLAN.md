# Plan

What we have decided to implement, or would like to implement, in intrepyd.
Each item says what and why; once an item is done, it moves to the bottom
with a reference to its commit.

The items that only concern intrepid are in its own plan, the `PLAN.md` of
the intrepid repository; the items that span both projects stay here, and
link to it for the intrepid side.

Items are numbered, so they can be referred to as #1, #2, and so on. The
numbers are shared with the plan of intrepid, so that a number names one item
across both projects: new items take the next free number of the two, and an
item keeps its number when it is done, dropped, or moved from one plan to the
other.

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
(`Dockerfile`, `Makefile.docker`, `docker/`, `.dockerignore`). The
repository mixes two products with different users and release cycles.
(`flask` and `gunicorn` are no longer install requirements of intrepyd since
#6, but the `rest` dependency group of `pyproject.toml`, which goes away with
the service.)

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

Status: implemented, not committed yet.

- `pyproject.toml` holds the metadata, with a PEP 639 license expression
  (`BSD-3-Clause AND LicenseRef-Intrepid AND MIT`) and the three license
  files; `setup.py` only tags the wheels; `setup.cfg`, `MANIFEST.in` and
  `requirements.txt` are gone. The wheel no longer installs `app/` as a top
  level package, which it used to.
- Runtime dependencies are only pandas and the antlr runtime; matplotlib is
  the `plots` extra; Flask and gunicorn, pylint, coverage and the release
  tools are dependency groups (`rest`, `lint`, `release`, `dev`), for
  `make install_dev`, an editable install that replaces `PYTHONPATH`.
- Releases: `make release` checks and pushes `v<VERSION>`, and
  `.github/workflows/release.yml` tests, builds the wheels, installs and
  checks each one on its platform (`tools/check_wheel.py`), publishes them on
  PyPI by trusted publishing, then makes a GitHub release whose notes are the
  `CHANGELOG.md` section of the version. `make undorelease` deletes the tag
  until the version reaches PyPI. Only wheels are published: an sdist could
  not be installed without the private intrepid library.
- Versions: `tools/check_release.py` requires a canonical PEP 440 `VERSION`
  later than every version on PyPI, a `CHANGELOG.md` section for it, and a
  tag that matches it.
- The first release of the new layout is 0.13.0 (0.12.0 is on PyPI already),
  described in `CHANGELOG.md`.

Still to do before the first release: on PyPI, add the trusted publisher
(owner `formalmethods`, repository `intrepyd`, workflow `release.yml`,
environment `pypi`); on GitHub, create the `pypi` environment.

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

### #8 Track the soundness of z3's Spacer

Moved to the plan of intrepid.

### #9 Engine based on invariants proposed by an AI

A new engine where an AI model reads the circuit (or the Lustre or IEC
61131-3 source it comes from) and proposes candidate invariants, and the
existing engines decide which ones are true. The AI is never trusted: a
candidate only counts once it is proved, so a wrong guess costs time, never a
wrong verdict.

The checking pipeline, cheapest first:

- simulation: random and directed traces falsify most wrong candidates at
  once;
- BMC: a candidate that fails within a few steps from the initial states is
  dropped, with its counterexample;
- induction: the candidates that survive are checked to hold initially and to
  be preserved by every step, together (Houdini style: drop the ones that
  fail, until the rest is inductive), possibly relative to the property; this
  is the same check that certifies the invariants of the PDR engine (#2);
- the inductive candidates then strengthen the property for k-induction,
  backward reachability or PDR, which may prove it where they could not
  alone.

What failed goes back to the AI: counterexamples to a candidate, or to the
induction of the property, are the most useful hint for the next round.

The AI is behind a small provider interface, so that the engine works with a
local model (for instance one served by llama.cpp, Ollama or vLLM, through
their OpenAI compatible HTTP API) or with a remote one through a stable
public API (such as the Anthropic Messages API), chosen by configuration,
with no change to the engine. A recorded, deterministic provider runs the
tests offline.

To settle: whether the orchestration lives in intrepyd (python, close to the
AI clients) with intrepid exposing an "is this invariant inductive" check in
its C API, or in intrepid itself; how the circuit is shown to the model
(source, or a textual rendering of the nets); the format of the candidates;
and how credentials and model choice are configured.

### #10 Run the engines in parallel, and stop at the first useful answer

A portfolio mode: given a model and its targets, run BMC, k-induction,
backward reachability and PDR at the same time, and stop all of them as soon
as one gives a conclusive answer (a counterexample, or a proof), returning it
together with which engine found it.

The engines are complementary, so this is worth having: on the Kind2
benchmarks BMC finds counterexamples fastest, while the proofs come from
different engines for different models (PDR proves many that nothing else
does, but backward reachability and k-induction still close some that PDR
does not). A portfolio gets the best of each, as Kind2 does by default, and
is also what #7 should compare against Kind2's portfolio.

Things to get right:

- isolation: one intrepid context, its z3 context and its net store are not
  meant to be shared between threads; either each engine runs in its own
  process, or in its own thread with its own context and a copy of the
  circuit (z3 can translate terms between contexts);
- stopping: the losers must be stopped promptly and cleanly, by killing the
  process or interrupting z3 (`Z3_interrupt`) in their thread;
- the result: the verdict, the engine, the time, and for a counterexample a
  trace that belongs to the caller's context;
- resources: how many engines run at once, on how many cores, with which
  overall timeout and memory limit; which engines take part, and with which
  settings (k-induction depth, int encoding for Lustre).

To settle: whether this lives in intrepyd (python processes, simplest) or in
intrepid's C API (threads, usable from C too). The AI engine of #9 could join
the portfolio later, as one more participant.

## Done

### #2 IC3/PDR engine

`Context.mk_pdr()`, the `engine.Pdr` class and the `pdr` engine kind of the
REST service, on top of the `Pdr` engine of intrepid v1.1.0 (see the plan of
intrepid), with tests and README (`8601eb5`). The engine finds inductive
invariants with z3's Spacer, and every proof it returns is certified (see
#8). On the Kind2 benchmarks, with a 10 second timeout, it solves 520 models
of 848 with int32 and 794 with unbounded integers, more than any other
engine; together, the engines solve 574 and 802.
