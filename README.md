# Intrepyd

Intre**py**d is a **python** module that provides a simulator and a model checker in form of
a rich API, to allow the rapid prototyping of **formal methods** algorithms
for the rigorous analysis of circuits, specifications, models.

Intrepyd also runs as a web service, with a rich REST API, in a Docker image:
see [intrepid-server](https://github.com/formalmethods/intrepid-server).

# Index

1. [Presentation](#presentation)
1. [Installation](#installation)
    1. [Supported Platforms](#supported-platforms)
    1. [Installing from PyPI](#installing-from-pypi)
    1. [Working from Source](#working-from-source)
    1. [Troubleshooting](#troubleshooting)
1. [Quick Start](#quick-start)
    1. [Constructing Models](#constructing-models)
    1. [Simulating Models](#simulating-models)
    1. [Model Checking](#model-checking)
    1. [Importing Models](#importing-models)
    1. [Benchmarking](#benchmarking)
    1. [Model Checking in the Cloud](#model-checking-in-the-cloud)
    1. [API documentation](#api-documentation)
1. [Repository Layout](#repository-layout)
1. [Development](#development)
    1. [Releasing](#releasing)
1. [License](#license)
1. [Resources](#resources)
    1. [Formal Methods Little Corner](#formal-methods-little-corner)
    1. [Bug reporting](#bug-reporting)
    1. [Feedback](#feedback)

# Presentation

A presentation video may be found [here](https://youtu.be/n-0Y_iJqkqY).

Intrepyd is built in two layers:

- **intrepid** — a C++17 model checking library built on the
  [Z3](https://github.com/Z3Prover/z3) SMT solver. It provides a net/circuit
  representation, an unroller, and four engines: bounded model checking (with
  k-induction), backward reachability, IC3/PDR, and a simulator. It is
  developed in a separate, private repository and comes here as a prebuilt
  shared library, `libintrepid`, with a plain C API.
- **intrepyd** — this python package. `intrepyd/api.py` loads `libintrepid`
  with `ctypes`; on top of it come a portfolio that runs the engines in
  parallel, front-ends for Lustre and IEC 61131-3 Structured Text, and
  pandas-based traces. Its REST service, with the Docker image, is a project
  of its own, [intrepid-server](https://github.com/formalmethods/intrepid-server).

Intrepyd itself is pure python: there is nothing to compile, and one build of
the library serves every python version.

# Installation

## Supported Platforms

|            | Status                                                     |
| ---------- | ---------------------------------------------------------- |
| Linux      | x86-64, glibc 2.28 or newer                                |
| Windows 10 | x86-64, needs the [Visual C++ Redistributable][1]          |
| Python     | 3.11 or newer                                              |

Only 64 bit architectures are supported. macOS is not supported.

## Installing from PyPI

```
pip install intrepyd
```

Each wheel carries the intrepid library for its platform, so there is nothing
else to install; `pip install intrepyd[plots]` also installs matplotlib, which
`intrepyd.plots` needs. If you want an isolated environment:

```
python3 -m venv venv
source venv/bin/activate
pip install intrepyd
```

## Working from Source

```
git clone https://github.com/formalmethods/intrepyd.git
cd intrepyd
make bootstrap_linux
make
```

`make bootstrap_linux` installs `make`, `git`, `python3-venv` and `python3-pip`
with `sudo apt`, creates a virtualenv in `venv/`, and runs `make install_dev`
in it. That installs intrepyd in editable mode, so the virtualenv imports it
from the checkout, together with what developing it needs: the `dev`
dependency group of `pyproject.toml` (pylint, coverage, the release tools,
matplotlib). In a virtualenv of your own, run
`make install_dev` directly; it needs pip 25.1 or newer, and upgrades pip
first.

Activating the virtualenv is optional for `make`: when `venv/` exists and no
other virtualenv is active, every target uses `venv/bin/python`. Pass
`PYTHON=...` to pick another interpreter, and `HOST_PYTHON=...` to choose the
one the bootstrap targets create `venv/` with.

### The intrepid library

`intrepyd/api.py` loads the library from `intrepyd/` itself, where
`make fetch_intrepid` puts it (the default `make` target starts with it). That
downloads, for the current platform, the release of intrepid named in
`INTREPID_VERSION` from the
[formalmethods/intrepid](https://github.com/formalmethods/intrepid) releases.
The repository is private, so the download needs a GitHub token with read
access to it, from `GITHUB_TOKEN` or from `gh auth login`.

To work against a local checkout of intrepid instead, build it there and point
`INTREPID_DIR` at it:

```
make -C ../intrepid build
make fetch_intrepid INTREPID_DIR=../intrepid
```

`INTREPID_DIR` also takes a release archive, or an extracted one. Finally, the
`INTREPID_LIBRARY` environment variable overrides all of this at run time: set
it to the path of a library file and `intrepyd.api` loads that one.

`make fetch_intrepid` also copies the library's license to
`intrepyd/LICENSE.intrepid`, and its header to `.intrepid/Intrepid.h`, where
`intrepyd/tests/test_api.py` checks that the binding matches the C API
function by function.

### Make targets

The default `make` target runs the whole pipeline:

| Target                 | What it does                                                       |
| ---------------------- | ------------------------------------------------------------------ |
| `fetch_intrepid`       | Puts the intrepid library into `intrepyd/` (see above)             |
| `all_linters`          | Runs pylint over `intrepyd` (fails below the score in `.pylintrc`)  |
| `all_tests`            | Runs the python test suite                                         |

Other useful targets:

| Target                 | What it does                                                       |
| ---------------------- | ------------------------------------------------------------------ |
| `tests_python`         | Just the python tests (`intrepyd` and the binding)                  |
| `coverage_python`      | Python tests under coverage, HTML report into `htmlcov/`            |
| `install_dev`          | Editable install of intrepyd, with the `dev` dependency group       |
| `install_intrepyd`     | `pip install --user .`                                              |
| `wheel`                | A wheel for one platform into `dist/`, e.g. `make wheel PLATFORM=windows-x86_64` |
| `wheels`               | The wheels of both platforms                                       |
| `release`              | Tags `v<VERSION>` and pushes it, which publishes the release (see [Releasing](#releasing)) |
| `undorelease`          | Deletes the tag of a release whose CI failed, before it reaches PyPI |
| `build_docs`           | Regenerates `docs/` with pdoc3                                      |

All the wheels can be built on one machine, since nothing is compiled: each
one is tagged `py3-none-<platform>` and holds that platform's library. Wheels
are all there is: no source distribution is published, since it could not be
installed without the intrepid library, which is private.

## Troubleshooting

**`ImportError: Cannot find the intrepid library`**
`intrepyd/libintrepid.so` (`intrepid.dll` on Windows) is missing: run
`make fetch_intrepid`, or set `INTREPID_LIBRARY` to the path of a library.

**`fetch_intrepid` fails with `HTTP Error 404`**
Either the token cannot read the private intrepid repository, or the release
named in `INTREPID_VERSION` does not exist, or has no package for this
platform.

**`ensurepip is not available` when creating the virtualenv**
Debian and Ubuntu ship `venv` separately: install `python3-venv` and delete the
half-created `venv/` before running `make bootstrap_linux` again.

**A test fails with an error mentioning `trace.cpp`**
On an error, the intrepid library writes the API calls made so far to
`trace.cpp` in the current directory, as a C++ program that replays them. It is
a debugging aid, and safe to delete.

# Quick start

All the examples below are self-contained and can be pasted into a python
session.

## Constructing Models

A `Context` is the factory for everything: types, nets, engines and traces.
Models are circuits made of **inputs**, **latches** (state, i.e. memory
elements) and combinational **nets**.

```python
import intrepyd as ip

ctx = ip.Context()

# Types
bool_t = ctx.mk_boolean_type()
int8_t = ctx.mk_int8_type()
# also: int16/int32/int64, uint8/uint16/uint32/uint64,
#       real, int, float16/float32/float64

# Combinational logic
a = ctx.mk_input('a', bool_t)
b = ctx.mk_input('b', bool_t)
and_gate = ctx.mk_and(a, b)
ctx.mk_output(and_gate)

# State: a latch that starts at 0 and increments whenever b holds
counter = ctx.mk_latch('counter', int8_t)
ctx.set_latch_init_next(
    counter,
    ctx.mk_number('0', int8_t),
    ctx.mk_ite(b, ctx.mk_add(counter, ctx.mk_number('1', int8_t)), counter))
```

The usual operators are available as `mk_*` methods: `mk_not`, `mk_and`,
`mk_or`, `mk_xor`, `mk_iff`, `mk_add`, `mk_sub`, `mk_mul`, `mk_div`, `mk_mod`,
`mk_minus`, `mk_eq`, `mk_neq`, `mk_leq`, `mk_lt`, `mk_geq`, `mk_gt`, `mk_ite`,
and the `mk_cast_to_*` family. `ctx.mk_assumption(net)` constrains the search
to states where `net` holds.

Larger models are usually built by subclassing `intrepyd.circuit.Circuit` and
implementing `_mk_inputs` and `_mk_naked_circuit_impl`; this is what the Lustre
and Structured Text translators generate.

## Simulating Models

A `Trace` holds input values over time. The simulator propagates them through
the circuit and fills in the watched nets.

```python
import intrepyd as ip

ctx = ip.Context()
bool_t, int8_t = ctx.mk_boolean_type(), ctx.mk_int8_type()

tick = ctx.mk_input('tick', bool_t)
count = ctx.mk_latch('count', int8_t)
ctx.set_latch_init_next(
    count,
    ctx.mk_number('0', int8_t),
    ctx.mk_ite(tick, ctx.mk_add(count, ctx.mk_number('1', int8_t)), count))

trace = ctx.mk_trace()
for depth in range(5):
    trace.set_value(tick, depth, 'true' if depth % 2 == 0 else 'false')

simulator = ctx.mk_simulator()
simulator.add_watch(count)
simulator.simulate(trace, 4)

print(trace.get_as_dataframe(ctx.net2name))
```

```
       0  1  2  3  4
tick   T  F  T  F  T
count  0  1  1  2  2
```

Booleans are `T` / `F`, and `?` marks a value the engine left unconstrained.
Traces are also available as plain dictionaries via `get_as_net_dictionary()`
and `get_as_depth_dictionary()`, and can be round-tripped through pandas with
`set_from_dataframe()`. `intrepyd.tools.simulate()` wraps this into a
CSV-driven workflow.

## Model Checking

A *target* is a net you ask the engine to make true. Proving a safety property
means showing that its negation is an unreachable target.

### Bounded model checking

BMC looks for a counterexample at exactly the current depth, so it is driven
incrementally from 0 upwards. `REACHABLE` means a counterexample was found;
`UNKNOWN` means none exists **within that bound**, which is not a proof.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int8_t = ctx.mk_int8_type()

c = ctx.mk_latch('c', int8_t)
ctx.set_latch_init_next(c, ctx.mk_number('0', int8_t),
                        ctx.mk_add(c, ctx.mk_number('1', int8_t)))
bad = ctx.mk_eq(c, ctx.mk_number('5', int8_t))

bmc = ctx.mk_bmc()
bmc.add_target(bad)
bmc.add_watch(c)
for depth in range(20):
    bmc.set_current_depth(depth)
    if bmc.reach_targets() == EngineResult.REACHABLE:
        print(f'counterexample at depth {depth}')
        print(bmc.get_last_trace().get_as_dataframe(ctx.net2name))
        break
```

```
counterexample at depth 5
   0  1  2  3  4  5
c  0  1  2  3  4  5
```

Call `bmc.set_allow_targets_at_any_depth()` to accept a target that becomes
true anywhere up to the current depth instead of exactly at it.

### Backward reachability

Backward reachability is unbounded: it can answer `UNREACHABLE`, which *is* a
proof.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()

flag = ctx.mk_latch('flag', bool_t)
ctx.set_latch_init_next(flag, ctx.mk_false(), flag)   # false forever

br = ctx.mk_backward_reach()
br.add_target(flag)
assert br.reach_targets() == EngineResult.UNREACHABLE
```

### k-induction

BMC can also prove properties, by turning on induction:

```python
bmc = ctx.mk_bmc()
bmc.set_use_induction()
bmc.add_target(target)
for depth in range(100):
    bmc.set_current_depth(depth)
    result = bmc.reach_targets()
    if result != EngineResult.UNKNOWN:
        break                       # REACHABLE or UNREACHABLE, both conclusive
```

The three results mean:

| Result        | Meaning                                                       |
| ------------- | ------------------------------------------------------------- |
| `REACHABLE`   | Target reached; `get_last_trace()` returns the counterexample  |
| `UNREACHABLE` | Proof that the target can never be reached                     |
| `UNKNOWN`     | No answer (for plain BMC: nothing found within the bound)      |

`mk_optimizing_bmc()` returns a BMC engine backed by the Z3 optimizer, for
finding minimal-cost counterexamples.

### IC3/PDR

`mk_pdr()` returns an IC3/PDR engine, built on Spacer, the one of Z3. Like
backward reachability it answers in one call, and can prove a target
unreachable; it does so by finding an inductive invariant, which is often
possible where k-induction and backward reachability get nowhere:

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int_t = ctx.mk_int_type()

c = ctx.mk_latch('c', int_t)
ctx.set_latch_init_next(c, ctx.mk_number('0', int_t),
                        ctx.mk_add(c, ctx.mk_number('1', int_t)))

pdr = ctx.mk_pdr()
pdr.add_target(ctx.mk_eq(c, ctx.mk_number('-1', int_t)))
assert pdr.reach_targets() == EngineResult.UNREACHABLE   # invariant: c >= 0
```

k-induction cannot prove this one, as `-2, -1` is a path that ignores the
initial state, and backward reachability would follow `-1, -2, -3, ...` for
ever. When a target is reachable, the counterexample comes from BMC, so
`get_last_trace()` returns a shortest one.

Proofs are checked: before answering `UNREACHABLE`, the engine verifies that
the invariant found holds initially, is preserved by every step, and excludes
the targets. If it does not, which can happen with some versions of Z3, the
answer is `UNKNOWN` rather than a wrong proof.

PDR is at its best on unbounded integers (`mk_int_type()`, or
`inttype='int'` when translating Lustre); it also handles fixed width
integers, but bit-vector invariants are harder to find.

### Portfolio

The engines are complementary: BMC finds counterexamples fastest, and
k-induction, backward reachability and PDR each prove properties the others
cannot. `mk_portfolio()` runs them all at the same time, and stops them as
soon as one gives a conclusive answer:

```python
portfolio = ctx.mk_portfolio()          # or engines=('kind', 'pdr'), max_depth=50
portfolio.add_target(bad)
portfolio.add_watch(c)
result = portfolio.reach_targets(timeout=60)
print(result, portfolio.get_last_engine(), portfolio.get_last_time())
if result == EngineResult.REACHABLE:
    print(portfolio.get_last_trace().get_as_dataframe(ctx.net2name))
```

The engines are `bmc`, `kind` (k-induction), `br` (backward reachability)
and `pdr`, all of them by default; `max_depth` bounds the depths that `bmc`
and `kind` try, which are unbounded by default. `reach_targets()` returns the
first `REACHABLE` or `UNREACHABLE` answer, or `UNKNOWN` if every engine gives
up or `timeout` seconds pass first; `get_last_engine()` says which engine
answered, and `get_last_errors()` reports the engines that failed.

Each engine runs in a process of its own, so the portfolio uses as many
cores as engines, and stopping the others is immediate. Each process builds
the circuit again from the *recipe* of the context: every context records the
calls that build its circuit, so a circuit must be built through the methods
of `Context` (as the Lustre and Structured Text translators and the parser
do), not through `intrepyd.api` directly. The counterexample of a
`REACHABLE` answer is rebuilt in the caller's context, by BMC at the depth the
engine found, the first time `get_last_trace()` is called.

The processes are started with `multiprocessing`, which imports the main
module of the program in each of them: a script that uses a portfolio must
keep its top level code under `if __name__ == '__main__':`.

## Importing Models

Rather than building circuits by hand, you can translate existing models. Both
translators emit a python module that you then import and instantiate.

### Lustre

```python
import intrepyd as ip
from intrepyd.tools import translate_lustre
from intrepyd.engine import EngineResult

encoding = translate_lustre('intrepyd/tests/lustre/peterson_1.lus',
                            'top', 'real', 'encoding')

ctx = ip.Context()
circuit = encoding.mk_instance(ctx, 'peterson')
circuit.mk_circuit()

br = ctx.mk_backward_reach()
br.add_target(ctx.mk_not(circuit.outputs['OK']))
print(br.reach_targets())      # EngineResult.UNREACHABLE -- property proved
```

The third argument selects how Lustre `real` is encoded: `'real'` for exact
rationals, or `'float32'` / `'float64'` for floating point.

The `inttype` argument selects how Lustre `int` is encoded:

| `inttype`            | Encoding                                                         |
| -------------------- | ---------------------------------------------------------------- |
| `'int32'` (default)  | 32 bit machine integers, as bit-vectors: arithmetic can overflow |
| `'int'`              | Unbounded integers, the semantics of Lustre itself               |
| `'int8'`, `'int16'`, `'int64'` | Machine integers of that width                         |

```python
encoding = translate_lustre('model.lus', 'top', 'real', 'encoding', inttype='int')
```

The two encodings can give different verdicts. With `x >= 0 => x + 1 > 0`, for
instance, `'int'` proves the property, while `'int32'` finds the counterexample
`x = 2147483647`, where `x + 1` overflows. Unbounded integers are also much
easier for the engines: on the Kind2 benchmarks shipped in `benchmarks/`, with
a 10 second timeout, k-induction solves 617 of the 848 models with `'int'`
against 495 with `'int32'`, and backward reachability 665 against 382.

### IEC 61131-3 Structured Text (PLCopen XML)

```python
from intrepyd.tools import translate_iec61131

encoding = translate_iec61131('intrepyd/tests/openplc/simple1.xml', 'encoding')
```

### Intrepid's own syntax

`intrepyd.parser.Parser` reads circuits written in a line-based syntax, one
net per line, `<name> = <operator> <arguments>`, and returns a populated
`Context`:

```
i1 = input bool
i2 = input bool
a1 = and i1 i2
l1 = latch bool
set_latch_init_next l1 true false
n0 = number 0 int8
```

```python
from intrepyd.parser import Parser

ctx = Parser().parse_file('model.txt')      # or parse_stream(stream)
target = ctx.nets['a1']
```

A line that does not parse raises `intrepyd.parser.ParseError`, with the line
number. The upload route of the REST service takes the same syntax.

## Benchmarking

`benchmarks/run_one.py` runs a single Lustre benchmark under one engine, in a
separate process, with a timeout:

```
python benchmarks/run_one.py <file.lus> <tool> [-t SECONDS] [--int-type int32|int]
```

`<tool>` is `br` (backward reachability), `bmc`, `bmc_ti` (BMC with
k-induction), `pdr`, or `portfolio` (all of them in parallel); the default
timeout is 60 seconds. It prints the verdict — `Valid`, `Invalid`, `Unknown`,
`Timeout` or `Exception` — and the elapsed time, followed, for `portfolio`, by
the engine that gave the verdict.
The benchmark expects the top node to be called `top` and to expose an `OK`
output, which is the Kind2 convention.

```
$ python benchmarks/run_one.py intrepyd/tests/lustre/peterson_1.lus br -t 30
intrepyd/tests/lustre/peterson_1.lus br Valid 0.018

$ python benchmarks/run_one.py intrepyd/tests/lustre/peterson_1.lus bmc -t 5
intrepyd/tests/lustre/peterson_1.lus bmc Timeout 5
```

Plain `bmc` times out here because bounded model checking cannot prove a
property, only refute it — which is what `bmc_ti` adds.

The driver translates into an `encoding.py` in the current directory and runs
the engine in a child process, so run it from a scratch directory, with the
python of a virtualenv where intrepyd is installed, such as the editable one
of `make install_dev`.

`benchmarks/kind2_benchmarks.py` runs the whole Kind2 benchmark suite listed in
`benchmarks/kind2-benchmarks.txt`; sample output from a 5 second timeout run is
kept in `benchmarks/results_5_seconds/`.

## Model Checking in the Cloud

Intrepyd also runs as a REST service, served by gunicorn in a Docker image:

```
docker run -p 8000:8000 ghcr.io/formalmethods/intrepid-server
```

The service, its API and its image are a project of their own,
[intrepid-server](https://github.com/formalmethods/intrepid-server), which
installs intrepyd from PyPI and is released on its own schedule.

## Api Documentation

The documentation for the python API can be found
[here](https://github.com/formalmethods/intrepyd/tree/main/docs/intrepyd),
and is regenerated with `make build_docs`.

# Repository Layout

| Path                    | Contents                                                        |
| ----------------------- | --------------------------------------------------------------- |
| `intrepyd/`             | The python package                                              |
| `intrepyd/api.py`       | `ctypes` binding of the intrepid C API                          |
| `intrepyd/lustre2py/`   | Lustre front-end (ANTLR generated)                              |
| `intrepyd/iec611312py/` | IEC 61131-3 Structured Text front-end                           |
| `intrepyd/tests/`       | Python test suite                                               |
| `benchmarks/`           | Benchmark drivers and results                                   |
| `fetch_intrepid.py`     | Puts the intrepid library into `intrepyd/`                      |
| `pyproject.toml`        | Package metadata, dependencies and development dependency groups |
| `setup.py`              | Tags each wheel for the platform of the library it holds        |
| `VERSION`               | The version of intrepyd                                         |
| `INTREPID_VERSION`      | The release of intrepid this version of intrepyd is built on    |
| `CHANGELOG.md`          | The changes of each release, which become its release notes     |
| `docs/pypi.md`          | The description shown on PyPI                                   |
| `tools/`                | Release checks: `check_release.py`, `check_wheel.py`            |

# Development

`intrepyd/api.py` exposes each function of intrepid's C API, `Intrepid.h`,
under the same name. Strings go in and come out as `str`, handles are opaque
values (`None` for `NULL`), nets are ints, and an error reported by the library
raises `RuntimeError`. The rest of intrepyd only talks to the library through
this module.

To move to a new release of intrepid, update `INTREPID_VERSION` and run
`make fetch_intrepid` and `make`. If the C API changed, `test_api.py` reports
the functions whose signature no longer matches; update the `_bind` lines in
`api.py` to follow.

The CI uses the library like everything else: the GitHub workflow in
`.github/workflows/test.yml` fetches it on every run, then lints and tests under several python versions, on Linux and Windows. Since
intrepid is private, the workflow needs a repository secret `INTREPID_TOKEN`:
a fine-grained personal access token with read access to the contents of
formalmethods/intrepid.

## Releasing

Releases are published by CI, from a tag `v<VERSION>`; nothing is uploaded by
hand. To make one:

1. Set `VERSION` to the new version: PyPI never accepts a version twice, so it
   must be later than every version already there. Set `INTREPID_VERSION` to
   the intrepid release to build on, if it changed.
2. Add a `## <VERSION>` section to `CHANGELOG.md`, saying what changed for
   users: it becomes the notes of the release.
3. Commit, push to `main`, wait for the tests to pass, then run
   `make release`.

`make release` refuses if the working tree has uncommitted changes, if the
branch is not `main` or is not pushed, if the tag already exists, if PyPI
already has `VERSION` or a later version, if `CHANGELOG.md` has no section for
it, or if the intrepid release in `INTREPID_VERSION` cannot be found (this
uses `gh`). Otherwise it tags the commit and pushes the tag, which starts
`.github/workflows/release.yml`:

1. the tests of `test.yml`, on every platform and python version;
2. the version checks again, against the tag;
3. the wheels of both platforms, built with `make wheels`;
4. each wheel installed on its platform, under python 3.11 and 3.13, and
   checked by `tools/check_wheel.py`: version, license files, contents, and
   every engine on a small model;
5. the wheels published on PyPI;
6. a GitHub release with the wheels and the `CHANGELOG.md` section.

Nothing is published unless every check succeeds. If the workflow fails
before PyPI, fix the cause, run `make undorelease` to delete the tag, then
commit, push and `make release` again; once the version is on PyPI,
`make undorelease` refuses, and the fix needs a new version. If only the
GitHub release fails, re-run it from the GitHub Actions page.

PyPI accepts the wheels through trusted publishing, without a token. This is
set up once, on PyPI, in the publishing settings of the intrepyd project: add
a GitHub publisher with owner `formalmethods`, repository `intrepyd`,
workflow `release.yml` and environment `pypi`; and, on GitHub, create the
environment `pypi` in the settings of the repository (it can require a
manual approval before each upload).

Once a release is on PyPI, intrepid-server can move to it: its
`requirements.txt` pins the version of intrepyd its image ships.

# License

Intrepyd is released under the BSD 3-Clause license, see
[LICENSE.md](LICENSE.md). The intrepid library it bundles is proprietary; its
license, installed as `intrepyd/LICENSE.intrepid`, allows it to be used and
redistributed freely, unmodified, as part of intrepyd.

# Resources

## Formal Methods Little Corner

A collection of experiences using Intrepyd can be found
[here](https://formalmethods.github.io).

## Bug reporting

Please report any bug you should experience
[here](https://github.com/formalmethods/intrepyd/issues).

## Feedback

If you wish to drop a feedback you may write to
`roberto.bruttomesso@gmail.com`.

[1]: https://aka.ms/vs/16/release/vc_redist.x64.exe
