# Releasing

## The order of the repositories

A change that crosses repositories is released from the bottom up:

1. **intrepid-dependencies**, if the z3 packages changed;
2. **intrepid**, which produces a new `libintrepid` release (its developer
   guide, in the intrepid repository, covers its own release);
3. **intrepyd**, as below, built on that intrepid release;
4. **intrepid-server**, by bumping the `intrepyd==X.Y.Z` pin in its
   `requirements.txt` once the intrepyd release is on PyPI.

## Releasing intrepyd

Releases are published by CI, from a tag `v<VERSION>`; nothing is uploaded by
hand. To make one:

1. Set `VERSION` to the new version. PyPI never accepts a version twice, so it
   must be later than every version already there. Set `INTREPID_VERSION` to
   the intrepid release to build on, if it changed.
2. Add a `## <VERSION>` section to `CHANGELOG.md`, saying what changed for
   users: it becomes the notes of the release.
3. Commit, push to `main`, wait for the tests to pass, then run `make release`.

`make release` refuses if the working tree has uncommitted changes, if the
branch is not `main` or is not pushed, if the tag already exists, if PyPI
already has `VERSION` or a later version, if `CHANGELOG.md` has no section for
it, or if the intrepid release in `INTREPID_VERSION` is not published with a
package for every platform (`fetch_intrepid.py --check` for each, so the release
workflow cannot tag and then fail downloading a library that is not there yet —
for instance when the pin was bumped to an intrepid release that has not
finished publishing). Otherwise it tags the commit and pushes the tag, which
starts `.github/workflows/release.yml`:

1. the tests of `test.yml`, on every platform and python version;
2. the version checks again, against the tag;
3. the wheels of both platforms, built with `make wheels`;
4. each wheel installed on its platform, under python 3.11 and 3.13, and
   checked by `tools/check_wheel.py`: version, license files, contents, and
   every engine on a small model;
5. the wheels published on PyPI;
6. a GitHub release with the wheels and the `CHANGELOG.md` section.

Nothing is published unless every check succeeds.

!!! tip "If the workflow fails"
    If it fails before PyPI, fix the cause, run `make undorelease` to delete
    the tag, then commit, push and `make release` again. Once the version is
    on PyPI, `make undorelease` refuses, and the fix needs a new version. If
    only the GitHub release step fails, re-run it from the Actions page.

## Trusted publishing

PyPI accepts the wheels through trusted publishing, without a token. This is
set up once, on PyPI, in the publishing settings of the intrepyd project: add a
GitHub publisher with owner `formalmethods`, repository `intrepyd`, workflow
`release.yml` and environment `pypi`; and, on GitHub, create the environment
`pypi` in the repository settings (it can require a manual approval before each
upload).

## The library and the token

The CI uses `libintrepid` like everything else: the workflow fetches it on
every run, then lints and tests under several python versions, on Linux and
Windows. Since intrepid is private, the workflow needs a repository secret
`INTREPID_TOKEN`: a fine-grained personal access token with read access to the
contents of `formalmethods/intrepid`.

The documentation site is published separately, by
`.github/workflows/docs.yml`, which needs no token because it reads the sources
statically (see [the docs build](../index.md)).
