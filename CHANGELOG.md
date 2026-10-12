# Changelog

The changes of each release of intrepyd. A release is made from the section
whose heading is the version in `VERSION`: `make release` refuses without
one, and the section becomes the notes of the GitHub release.

## 0.22.0

- **MC/DC tests for circuit diagrams.** `intrepyd.diagram.conditions(doc,
  decision)` finds a decision's conditions, walking back from its block
  through the boolean operators and the pins of sub-systems to the first nets
  that are none of them (inputs, latches, comparisons, library blocks' outputs,
  or blocks named in `stops`); `intrepyd.diagram.mcdc(doc, decisions)` and
  `python -m intrepyd.diagram mcdc FILE` (`--decision`, `--depth`,
  `--timeout`, or the diagram's new `testgen` section) generate a pair of
  tests per condition (masking MC/DC) on two copies of the circuit, each
  searched by the portfolio, and give each test as a run (its inputs, every
  block's values) with its conditions and decision at its last step, and each
  condition as covered, unreachable or unknown. The intrepid-vscode editor runs
  it.
- `intrepyd.diagram.Circuit` has `input_types`, the type of each input block.
- The trace of a failing assertion or a reached target (`intrepyd.diagram
  verify`) gives a concrete value to each input the engine leaves free
  (false, or 0), where it gave none: the trace is replayed as it is, and an
  input with no value at a step but one later no longer crashes the
  simulator of intrepid up to 1.5.0.

## 0.21.0

- **The catalogue of `intrepyd.lib`**, `intrepyd.lib.catalogue`: every library
  block described as data — its label and description, its parameters, its
  input pins with their types (and whether they may stay unwired), its outputs
  with their types, and how to call it. `python -m intrepyd.diagram catalogue`
  prints it as JSON, so a tool (the intrepid-vscode editor's palette) offers
  the blocks without keeping its own copy of them; `intrepyd.diagram` builds
  the library blocks of a diagram from it.
- **Sub-systems in diagrams**: a `"kind": "subsystem"` block holds the blocks
  whose `"parent"` it is; its In blocks are its inputs, wired from outside by
  name, and its Out blocks its outputs. Sub-systems nest; they are flattened
  when the circuit is built, the names inside prefixed with the sub-system's
  (`"filter.acc"`), and a simulation gives a sub-system's outputs the values of
  its Out blocks.
- The counter of `intrepyd.lib.eda` (`mk_counter`) has all its pins in a
  diagram: `init`, `increment`, `enable` and `reset` may be wired, or left
  unwired for their defaults.
- **Proof certificates.** An engine that proves a target unreachable can say
  why, in a form anyone can check: `engine.set_produce_certificates()`, then
  `engine.get_last_certificate()` after an `UNREACHABLE` answer, an SMT-LIB 2
  script each of whose `check-sat` must answer `unsat` (`z3 proof.smt2`,
  `cvc5 proof.smt2`, ...). PDR and backward reachability give an inductive
  invariant, k-induction its base cases and its step. intrepid checks each
  certificate before giving it, and one that does not hold makes the answer
  `UNKNOWN`. The portfolio gives the winner's
  (`ctx.mk_portfolio(certificates=True)`), and `intrepyd.diagram verify`
  gives each proved property its `"certificate"` (`--certificates`, or
  `"certificates": true` in the diagram's `verification`). Needs intrepid 1.4
  or newer; with an older library the rest of intrepyd works as before, and
  asking for a certificate raises `RuntimeError` (a diagram's verification
  says so).
- **Portfolio fix:** when backward reachability or PDR was the first to find
  the counterexample of a circuit with no inputs, `get_last_trace()` raised
  `Cannot rebuild the counterexample` (the engine reported depth 0, and BMC
  found nothing there). The engines now watch the targets, and the trace has
  the depth of the counterexample.

## 0.20.0

Bump version

## 0.19.0

- **`intrepyd.diagram`: build and simulate circuit diagrams**, the documents
  (`*.intrepyd.json`) of the intrepid-vscode circuit editor. It is the inverse
  of `intrepyd.export`: `build()` turns a diagram into a `Context` — gates,
  gates with more than two inputs (chained), switches, casts, latches, the
  blocks of `intrepyd.lib` and their several outputs, Out blocks — and
  `simulate()` runs its stimuli and returns every block's value at every step.
  `verify()` checks the diagram's properties — Assertion blocks (must always
  hold) and Target blocks (to reach) — each with its own run of the portfolio
  (or one engine), and returns a verdict per property: *holds* / *fails*,
  *reached* / *unreachable*, or *unknown*; a failing assertion or a reached
  target comes with its trace, as the inputs at each step and every block's
  values along it. `python -m intrepyd.diagram simulate FILE` and `verify FILE`
  (`-` for standard input) print the result as JSON, for the editor to show.
  See the module's documentation for the format.
- Export schema version 2: each node carries the source `file` and `line` that
  built the net (when the recipe recorded it), so a viewer can jump from a
  block to the line of python that created it. Version 1 is the same without
  them; readers should accept both.
- Clearer errors from the circuit builders: `mk_*` now raise
  `intrepyd.context.IntrepydTypeError` with a readable message when an operand
  has the wrong type (e.g. a boolean operator on an integer, or a comparison of
  two different types), instead of letting an internal solver sort-mismatch
  surface. The check is conservative — it fires only when the operand types are
  known and clearly incompatible, so it never rejects a valid circuit.
- **Export fix: wires to shared or simplified nets.** When several calls return
  the same net, as `mk_true()` called twice, an expression the library builds
  once, or one it simplifies (`mk_and(ctx.mk_true(), x)` is `x`), the export
  lost the wires that used all but the last of those calls (a latch's initial
  value went missing), or turned the simplified call into a gate of its own
  (an AND on top of `x`, with doubled inputs and a loop). The recipe now
  records the net each call returned (`Recipe.results`), and the export defines
  a net by the first call that built it and treats the later ones as aliases.
  It also leaves out a `true`/`false` that nothing reads.
- The export can carry a **trace**: when the program also builds a simulation or
  a counterexample, `intrepyd.export` adds a `"trace"` with each watched net's
  value at each step, so a viewer can overlay the values on the blocks over
  time. Absent when no usable trace is built.

## 0.18.0

- Exporting nets, ready to be rendered

## 0.17.0

- Bumped intrepid to 1.3.0, failed in previous release

## 0.16.0

- Bumped intrepid to 1.3.0

## 0.15.0

- **New license:** intrepyd is now free for noncommercial purposes only
  (personal use, universities, public research organizations), under the
  PolyForm Noncommercial License 1.0.0; companies need a commercial license,
  to be requested from roberto.bruttomesso@gmail.com. Earlier versions stay
  under the BSD 3-Clause license. The intrepid library it bundles may be used
  as part of intrepyd within the same terms.
- **Remote contexts:** after `intrepyd.use_remote(url)`, every `Context` is
  a context on an [intrepid-server](https://github.com/formalmethods/intrepid-server)
  (1.1.0 or newer), with the same methods, engines, traces and simulators
  as a local one, so that a program runs unchanged against the service;
  `use_local()` goes back. See `intrepyd.remote`.
- `Context.pop_namespace()` with no namespace pushed raises, instead of
  crashing the library.
- `Trace.get_numeric_value()` reads the values of the next intrepid
  release: reals as fractions (`1/3`), and the infinities and NaN of floats
  (`inf`, `-inf`, `nan`).
- **Simulink:** `intrepyd.tools.translate_simulink()` translates a Simulink
  model, read without MATLAB, with its Stateflow charts, its bus objects and
  the models it refers to, into a circuit whose targets are its assertions
  and the runtime errors of its charts, and whose `nets` are the activity of
  the states of its charts. It needs the closed source library
  of intrepid-simulink, which is not bundled yet:
  `INTREPID_SIMULINK_LIBRARY` points to a local build of it.
- **Documentation site:** the documentation is now a
  [MkDocs](https://www.mkdocs.org/) site at
  <https://formalmethods.github.io/intrepyd/>, with a hands-on tutorial from a
  first netlist to a translated model, a guide from concepts to tasks, an API
  reference generated from the docstrings by mkdocstrings, and a developer guide
  (architecture, debugging, testing, performance, releasing).
  It is deployed automatically on every push to `main`, so it stays in sync
  with the code, and replaces the hand-committed pdoc3 output under `docs/`.
  `make build_docs` builds it, `make serve_docs` previews it, and the new
  `docs` dependency group installs what they need.

## 0.14.0

- **Portfolio:** `Context.mk_portfolio()` runs BMC, k-induction, backward
  reachability and PDR in parallel, each in a process of its own, and
  answers with the first of them to prove or refute the targets, saying
  which. Every context now records the calls that build its circuit, so that
  each process can build it again.
- **Python 3.11 or newer.**
- **The REST service and its Docker image have moved** to their own
  repository, [intrepid-server](https://github.com/formalmethods/intrepid-server),
  which installs intrepyd from PyPI; this repository is now only the python
  library.

## 0.13.0

The first release built on the new intrepid library, after four years.

- **One wheel per platform, for every python version.** intrepyd is now pure
  python: it loads the intrepid model checking library through `ctypes`
  instead of a SWIG module built for one python version. Wheels are
  published for Linux (x86-64, glibc 2.28 or newer) and Windows (x86-64),
  and do not depend on the python version. Earlier releases were source
  archives carrying prebuilt SWIG modules.
- **macOS is no longer supported.**
- **IC3/PDR engine:** `Context.mk_pdr()`, on top of Z3's Spacer. It proves
  many properties that k-induction and backward reachability cannot, and
  every proof it returns is checked.
- **Faster engines:** bounded model checking, k-induction and backward
  reachability solve more of the Kind2 Lustre benchmarks, in less time.
- **Unbounded integers for Lustre:** `translate_lustre(..., inttype='int')`
  encodes Lustre `int` as mathematical integers instead of 32 bit machine
  integers; the default is still `int32`.
- **Fewer dependencies:** installing intrepyd no longer installs Flask and
  gunicorn, which only the REST service needs; `pip install intrepyd[plots]`
  also installs matplotlib, which `intrepyd.plots` needs.
- Built on intrepid 1.1.0.
