# Changelog

The changes of each release of intrepyd. A release is made from the section
whose heading is the version in `VERSION`: `make release` refuses without
one, and the section becomes the notes of the GitHub release.

## 0.14.0

- **Portfolio:** `Context.mk_portfolio()` runs BMC, k-induction, backward
  reachability and PDR in parallel, each in a process of its own, and
  answers with the first of them to prove or refute the targets, saying
  which. Every context now records the calls that build its circuit, so that
  each process can build it again.
- **Python 3.11 or newer.**
- **The REST service and its Docker image have moved** to their own
  repository, [intrepyd-server](https://github.com/formalmethods/intrepyd-server),
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
