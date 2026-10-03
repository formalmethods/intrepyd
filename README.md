# Intrepyd

Intre**py**d is a **python** module that provides a simulator and a model checker in form of
a rich API, to allow the rapid prototyping of **formal methods** algorithms
for the rigorous analysis of circuits, specifications, models.

Intrepid may also be run as a containerized web service, which can be used interactively
via a rich REST API.

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
  representation, an unroller, and three engines: bounded model checking (with
  k-induction), backward reachability, and a simulator. It is developed in a
  separate, private repository and comes here as a prebuilt shared library,
  `libintrepid`, with a plain C API.
- **intrepyd** — this python package. `intrepyd/api.py` loads `libintrepid`
  with `ctypes`; on top of it come front-ends for Lustre and IEC 61131-3
  Structured Text, pandas-based traces, and a Flask REST service.

Intrepyd itself is pure python: there is nothing to compile, and one build of
the library serves every python version.

# Installation

## Supported Platforms

|            | Status                                                     |
| ---------- | ---------------------------------------------------------- |
| Linux      | x86-64, glibc 2.28 or newer                                |
| Windows 10 | x86-64, needs the [Visual C++ Redistributable][1]          |
| Python     | 3.9 or newer                                               |

Only 64 bit architectures are supported. macOS is not supported.

## Installing from PyPI

```
pip install intrepyd
```

Each wheel carries the intrepid library for its platform, so there is nothing
else to install. If you want an isolated environment:

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
with `sudo apt`, creates a virtualenv in `venv/`, and installs the python
requirements into it.

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
| `tests_python`         | Just the python tests (`intrepyd`, the binding and the REST API)    |
| `coverage_python`      | Python tests under coverage, HTML report into `htmlcov/`            |
| `install_intrepyd`     | `pip install --user .`                                              |
| `wheel`                | A wheel for one platform into `dist/`, e.g. `make wheel PLATFORM=windows-x86_64` |
| `wheels`               | The wheels of both platforms                                       |
| `release_intrepyd_pip` | Builds all the wheels and uploads them to PyPI                      |
| `build_docs`           | Regenerates `docs/` with pdoc3                                      |

All the wheels can be built on one machine, since nothing is compiled: each
one is tagged `py3-none-<platform>` and holds that platform's library.

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

### IEC 61131-3 Structured Text (PLCopen XML)

```python
from intrepyd.tools import translate_iec61131

encoding = translate_iec61131('intrepyd/tests/openplc/simple1.xml', 'encoding')
```

## Benchmarking

`benchmarks/run_one.py` runs a single Lustre benchmark under one engine, in a
separate process, with a timeout:

```
python benchmarks/run_one.py <file.lus> <tool> [-t SECONDS]
```

`<tool>` is `br` (backward reachability), `bmc`, or `bmc_ti` (BMC with
k-induction); the default timeout is 60 seconds. It prints the verdict —
`Valid`, `Invalid`, `Unknown`, `Timeout` or `Exception` — and the elapsed time.
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
the engine in a child process, so run it from a scratch directory and make sure
the repository root is on `PYTHONPATH`.

`benchmarks/kind2_benchmarks.py` runs the whole Kind2 benchmark suite listed in
`benchmarks/kind2-benchmarks.txt`; sample output from a 5 second timeout run is
kept in `benchmarks/results_5_seconds/`.

## Model Checking in the Cloud

Intrepid also runs as a REST service. From a container:

```
docker run -p 8000:8000 robertobruttomesso/intrepid
```

or, from a source checkout, in development mode:

```
./start_development_server.sh          # flask, port 5000
```

or in production mode, exactly as the container does:

```
gunicorn -b 0.0.0.0:8000 intrepid:app
```

All routes are under `/api/v1/`. A complete session — build `a AND b`, ask BMC
to reach it, and read back the counterexample:

```
BASE=http://127.0.0.1:8000/api/v1

curl -X POST $BASE/contexts/create -H 'Content-Type: application/json' \
     -d '{"name":"demo"}'
# {"result":"demo"}

curl -X POST $BASE/inputs/create -H 'Content-Type: application/json' \
     -d '{"context":"demo","type":"bool"}'
# {"result":"__i0"}
curl -X POST $BASE/inputs/create -H 'Content-Type: application/json' \
     -d '{"context":"demo","type":"bool"}'
# {"result":"__i1"}

curl -X POST $BASE/nets/ands/create -H 'Content-Type: application/json' \
     -d '{"context":"demo","x":"__i0","y":"__i1"}'
# {"result":"__n10"}

curl -X POST $BASE/engines/create -H 'Content-Type: application/json' \
     -d '{"context":"demo","engine":"bmc"}'
# {"result":"e0"}

curl -X PUT $BASE/engines/addtarget -H 'Content-Type: application/json' \
     -d '{"context":"demo","engine":"e0","net":"__n10"}'
curl -X PUT $BASE/engines/setcurrentdepth -H 'Content-Type: application/json' \
     -d '{"context":"demo","engine":"e0","depth":0}'
curl -X PUT $BASE/engines/reachtargets -H 'Content-Type: application/json' \
     -d '{"context":"demo","engine":"e0"}'
# {"result":"reachable"}

curl -X GET "$BASE/engines/lasttrace?context=demo&engine=e0"
# {"result":"t0"}
curl -X GET "$BASE/traces/values?context=demo&trace=t0"
# {"result":{"__i0":["T"],"__i1":["T"]}}
```

Engine kinds are `bmc`, `optimizing_bmc` and `backward_reach`. Nets are created
under `/nets/<operator>s/create` (`ands`, `ors`, `nots`, `eqs`, `ites`,
`numbers`, ...); binary operators take `x` and `y`, unary ones take `x`.

Instead of issuing one request per net, you can `POST` a whole model to
`/upload` and get a populated context back. It expects Intrepid's own
line-based syntax, one net per line, `<name> = <operator> <arguments>`:

```
i1 = input bool
i2 = input bool
a1 = and i1 i2
l1 = latch bool
set_latch_init_next l1 true false
n0 = number 0 int8
```

```
curl -X POST $BASE/upload -F 'file=@model.txt'
# {"result":{"ctx":"__ctx0"}}
```

The same syntax is available in-process through `intrepyd.parser.Parser`, with
`parse_file()` and `parse_stream()`.

Container images are published on
[Docker Hub](https://hub.docker.com/r/robertobruttomesso/intrepid), and
`Makefile.docker` has targets for building and pushing to Docker Hub, the
GitHub container registry, Heroku and AWS ECR.

## Api Documentation

The documentation for the python API can be found
[here](https://github.com/formalmethods/intrepid/tree/master/docs/intrepyd),
and is regenerated with `make build_docs`.

The documentation for the REST API can be found
[here](https://www.postman.com/robertobruttomesso/workspace/intrepid-model-checker-rest-api).

# Repository Layout

| Path                    | Contents                                                        |
| ----------------------- | --------------------------------------------------------------- |
| `intrepyd/`             | The python package                                              |
| `intrepyd/api.py`       | `ctypes` binding of the intrepid C API                          |
| `intrepyd/lustre2py/`   | Lustre front-end (ANTLR generated)                              |
| `intrepyd/iec611312py/` | IEC 61131-3 Structured Text front-end                           |
| `intrepyd/tests/`       | Python test suite                                               |
| `app/`                  | Flask blueprints implementing the REST API                      |
| `intrepid.py`           | REST service entry point (`intrepid:app`)                       |
| `benchmarks/`           | Benchmark drivers and results                                   |
| `fetch_intrepid.py`     | Puts the intrepid library into `intrepyd/`                      |
| `INTREPID_VERSION`      | The release of intrepid this version of intrepyd is built on    |

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

The Docker image and CI use the library like everything else:
`make -f Makefile.docker docker_build` fetches the linux one first, and the
GitHub workflow in `.github/workflows/test.yml` fetches it on every run, then
lints and tests under several python versions, on Linux and Windows. Since
intrepid is private, the workflow needs a repository secret `INTREPID_TOKEN`:
a fine-grained personal access token with read access to the contents of
formalmethods/intrepid.

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
[here](https://github.com/formalmethods/intrepid/issues).

## Feedback

If you wish to drop a feedback you may write to
`roberto.bruttomesso@gmail.com`.

[1]: https://aka.ms/vs/16/release/vc_redist.x64.exe
