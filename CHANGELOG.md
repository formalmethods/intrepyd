# Changelog

The changes of each release of intrepyd. A release is made from the section
whose heading is the version in `VERSION`: `make release` refuses without
one, and the section becomes the notes of the GitHub release.

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
