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
1. [Documentation](#documentation)
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
  pandas-based traces. The front-end for Simulink models is a library of its
  own too, closed source as intrepid is, which intrepyd loads when present. Its REST service, with the Docker image, is a project
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
| `build_docs`           | Builds the documentation site into `site/` with MkDocs             |
| `serve_docs`           | Previews the documentation site locally, rebuilding on change      |

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

Everything is built from a `Context`: types, nets, engines and traces. Here is
a counter proved never to go negative, which you can paste into a python
session:

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

Models are circuits of **inputs**, **latches** (state) and combinational
**nets**; you build them with the `mk_*` methods, or translate them from
Lustre, IEC 61131-3 Structured Text or Simulink. A **target** is a net you ask
an engine to reach: `REACHABLE` returns a counterexample trace, `UNREACHABLE`
is a proof, `UNKNOWN` is no answer. The engines — BMC, k-induction, backward
reachability and IC3/PDR — are complementary, and `mk_portfolio()` runs them in
parallel.

The full walk-through — building and simulating models, each engine and what it
proves, the portfolio, importing models, benchmarking and the REST service — is
in the documentation.

# Documentation

The documentation lives at **<https://formalmethods.github.io/intrepyd/>**: a
guide from concepts to tasks, and an API reference generated from the sources.
It is built with [MkDocs](https://www.mkdocs.org/) (see `mkdocs.yml`) and
published automatically by the `docs` workflow on every push to `main`, so it
always matches the code; the API reference is produced from the docstrings by
[mkdocstrings](https://mkdocstrings.github.io/), so nothing generated is
committed.

To work on the docs locally, `make serve_docs` previews the site at
`http://127.0.0.1:8000`, rebuilding on every change, and `make build_docs`
builds it into `site/`. Both need the `docs` dependency group
(`make install_dev`, or `pip install -e . --group docs`).

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
| `mkdocs.yml`            | Configuration of the documentation site                         |
| `docs/`                 | Sources of the documentation site (guide and API reference)     |
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

Intrepyd is free for noncommercial purposes: personal use, and use by
educational institutions, public research organizations and the other
noncommercial organizations of the PolyForm Noncommercial License 1.0.0,
under which it is released from version 0.15.0 on, see
[LICENSE.md](LICENSE.md). Any other use, in particular by companies for a
commercial purpose, requires a commercial license: write to
`roberto.bruttomesso@gmail.com`. Versions up to 0.14.0 were released under
the BSD 3-Clause license.

The intrepid library it bundles is proprietary; its license, installed as
`intrepyd/LICENSE.intrepid`, allows it to be used and redistributed,
unmodified, as part of intrepyd, within the terms of the license of
intrepyd: any commercial use of the library, with any version of intrepyd,
needs a commercial license.

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
