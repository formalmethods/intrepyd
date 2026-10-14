# Testing

## The python suite

The tests live in `intrepyd/tests/`, one `test_*.py` per area, and run with the
standard library's `unittest`:

```bash
make tests_python            # python -m unittest discover -v
python -m unittest intrepyd.tests.test_bmc        # one module
```

What the modules cover:

| Module | Area |
| ------ | ---- |
| `test_api.py` | the `ctypes` binding matches the checked-in `Intrepid.h`, function by function |
| `test_circuit.py`, `test_simulator.py`, `test_trace.py` | building circuits, simulating, traces as dataframes |
| `test_bmc.py`, `test_br.py`, `test_pdr.py`, `test_engine.py` | each engine, and the common engine behaviour |
| `test_portfolio.py` | the parallel portfolio |
| `test_lustre.py`, `test_openplc.py`, `test_st*.py`, `test_simulink.py` | the front-ends |
| `test_parser.py`, `test_formula_*.py` | the line-based syntax and the formula parser |
| `test_lib_eda.py`, `test_lib_plc.py` | the component library |
| `test_scr.py`, `test_pseudoboolean.py`, `test_atg.py` | the helpers and MC/DC |
| `test_remote.py` | the REST client (skipped without a server) |

Tests that need the closed-source Simulink library are skipped unless
`INTREPID_SIMULINK_LIBRARY` points at a build of it (see
[importing models](../guide/importing.md#simulink)).

## Adding a test

Put it next to the others, in the module for its area, as a `unittest.TestCase`
subclass. Build the model through a `Context` (not through `api.py`), run the
engine or the simulator, and assert on the verdict and, where it matters, on
the counterexample read back from the trace — checking the value, not only that
some trace came out. Keep a test self-contained and fast; the whole suite runs
on every CI job, on Linux and Windows, under several python versions.

## Linting, type checking and coverage

```bash
make linter_python           # pylint, fails below the score in .pylintrc
make typecheck_python        # mypy on the annotated public API
make coverage_python         # the suite under coverage, HTML into htmlcov/
```

`make all` runs the linters and the tests together, which is what CI
(`.github/workflows/test.yml`) runs on every push and pull request.

The public API carries type annotations, and the package ships a `py.typed`
marker so editors and type checkers see them: a net is an `intrepyd.api.Net`
and a type an `intrepyd.api.Type`, not an opaque `Any`. `make typecheck_python`
runs mypy over the annotated modules, configured under `[tool.mypy]` in
`pyproject.toml`; it reads the sources statically, so it needs no intrepid
library. The checked surface includes `Context`, `Trace`, `Simulator`,
`Circuit`, the engines and portfolio, translation/simulation helpers,
pseudo-boolean helpers, and the EDA/PLC components. Every definition in those
modules must be annotated (`disallow_untyped_defs`), except the portfolio's
internal process/recipe helpers, whose bodies are checked with
`check_untyped_defs`. The dynamic binding and exporter are also checked.

`typing_tests/public_api.py` is a static consumer fixture, included in that
command. It asserts return types (including optional certificates and trace
dictionary keys), and checks that wrong argument types are rejected. Its
intentional errors use `type: ignore` with `warn_unused_ignores`, so silently
losing an annotation fails the check too. Do not execute this fixture.

Annotations are still being extended to the rest of the package, including
the remote client and other front-end/helper APIs. Add each module to mypy's
`files` list once its public surface is typed, then extend the strict override.
Third-party stubs such as `pandas-stubs` are optional; DataFrame internals are
not checked without them.

## The C++ suite

The engines themselves are tested in the **intrepid** repository, with a
gtest suite and a line-coverage gate; its developer guide covers it. The
python suite tests intrepyd on top of the library, so the two are
complementary: a bug in an engine is caught in intrepid, a bug in the binding
or the front-ends here. When a failure reaches into the library, reproduce it
there with the [API trace](debugging.md#the-api-trace).
