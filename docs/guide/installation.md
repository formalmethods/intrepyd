# Installation

## Supported platforms

|            | Status                                            |
| ---------- | ------------------------------------------------- |
| Linux      | x86-64, glibc 2.28 or newer                       |
| Windows 10 | x86-64, needs the Visual C++ Redistributable      |
| Python     | 3.11 or newer                                     |

Only 64-bit architectures are supported. macOS is not supported.

## Installing from PyPI

```bash
pip install intrepyd
```

Each wheel carries the intrepid library for its platform, so there is nothing
else to install. `pip install intrepyd[plots]` also installs matplotlib, which
[`intrepyd.plots`](../reference/helpers.md) needs. For an isolated environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install intrepyd
```

## Working from source

```bash
git clone https://github.com/formalmethods/intrepyd.git
cd intrepyd
make bootstrap_linux
make
```

`make bootstrap_linux` installs `make`, `git`, `python3-venv` and `python3-pip`
with `sudo apt`, creates a virtualenv in `venv/`, and runs `make install_dev`
in it. That installs intrepyd in editable mode together with the `dev`
dependency group of `pyproject.toml` (pylint, coverage, the release tools,
matplotlib). In a virtualenv of your own, run `make install_dev` directly; it
needs pip 25.1 or newer.

Activating the virtualenv is optional for `make`: when `venv/` exists and no
other virtualenv is active, every target uses `venv/bin/python`. Pass
`PYTHON=...` to pick another interpreter, and `HOST_PYTHON=...` to choose the
one the bootstrap targets create `venv/` with.

!!! note "The intrepid library"
    `intrepyd/api.py` loads the library from `intrepyd/` itself, where
    `make fetch_intrepid` puts it. That downloads, for the current platform,
    the release named in `INTREPID_VERSION` from the
    [formalmethods/intrepid](https://github.com/formalmethods/intrepid)
    releases. The repository is private, so the download needs a GitHub token
    with read access to it, from `GITHUB_TOKEN` or from `gh auth login`.

    To work against a local checkout of intrepid instead, build it there and
    point `INTREPID_DIR` at it:

    ```bash
    make -C ../intrepid build
    make fetch_intrepid INTREPID_DIR=../intrepid
    ```

    The `INTREPID_LIBRARY` environment variable overrides all of this at run
    time: set it to the path of a library file and `intrepyd.api` loads that
    one.

## Troubleshooting

!!! failure "`ImportError: Cannot find the intrepid library`"
    `intrepyd/libintrepid.so` (`intrepid.dll` on Windows) is missing: run
    `make fetch_intrepid`, or set `INTREPID_LIBRARY` to the path of a library.

!!! failure "`fetch_intrepid` fails with `HTTP Error 404`"
    Either the token cannot read the private intrepid repository, or the
    release named in `INTREPID_VERSION` does not exist, or has no package for
    this platform.

!!! failure "`ensurepip is not available` when creating the virtualenv"
    Debian and Ubuntu ship `venv` separately: install `python3-venv` and delete
    the half-created `venv/` before running `make bootstrap_linux` again.

!!! failure "A test fails with an error mentioning `trace.cpp`"
    On an error, the intrepid library writes the API calls made so far to
    `trace.cpp` in the current directory, as a C++ program that replays them.
    It is a debugging aid, and safe to delete.
