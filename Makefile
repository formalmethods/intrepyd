INTREPYD_SRC_PATH=intrepyd
APP_SRC_PATH=app

# PYTHON defaults to the virtualenv made by bootstrap_*, when there is one and
# no other virtualenv is active, so the targets work without activating it.
# HOST_PYTHON is the interpreter that creates that virtualenv.
HOST_PYTHON?=python3
ifeq ($(origin PYTHON),undefined)
ifeq ($(VIRTUAL_ENV)$(wildcard $(CURDIR)/venv/bin/python),$(CURDIR)/venv/bin/python)
PYTHON=$(CURDIR)/venv/bin/python
else
PYTHON=python3
endif
endif

# The intrepid backend is a separate project, used here as a prebuilt shared
# library. fetch_intrepid downloads the release named in INTREPID_VERSION for
# this platform; INTREPID_DIR uses a local build instead, e.g.
#   make fetch_intrepid INTREPID_DIR=../intrepid
# PLATFORM picks another platform's release, e.g. to build its wheel:
#   make wheel PLATFORM=windows-x86_64
INTREPID_DIR?=
PLATFORM?=
INTREPID_REPO=formalmethods/intrepid
INTREPID_VERSION:=$(shell cat INTREPID_VERSION)
VERSION:=$(shell cat VERSION)
# Where 'make release' pushes the tag v$(VERSION), and the branch it must be on
REMOTE?=origin
BRANCH?=main
FETCH_ARGS=$(if $(INTREPID_DIR),--from $(INTREPID_DIR),) \
           $(if $(PLATFORM),--platform $(PLATFORM),)

.PHONY: all all_linters all_tests bootstrap_linux install_dev fetch_intrepid \
	linter_python tests_python coverage_python install_intrepyd build_docs \
	serve_docs wheel wheels release undorelease

all: fetch_intrepid all_linters all_tests

all_linters: linter_python

all_tests: tests_python

bootstrap_linux:
	@sudo apt update && sudo apt install -y make git python3-venv python3-pip
	@$(HOST_PYTHON) -m venv venv
	@$(MAKE) --no-print-directory install_dev PYTHON=$(CURDIR)/venv/bin/python
	@echo '*** Activate the virtualenv with: source venv/bin/activate ***'

# intrepyd in editable mode, with what developing it needs: the dev group of
# pyproject.toml. Dependency groups need pip 25.1 or newer.
install_dev:
	@$(PYTHON) -m pip install --upgrade 'pip>=25.1'
	@$(PYTHON) -m pip install -e . --group dev

fetch_intrepid:
	@$(PYTHON) fetch_intrepid.py $(FETCH_ARGS)

# Fails if the score drops below fail-under in .pylintrc
linter_python:
	@$(PYTHON) -m pylint intrepyd

tests_python:
	@echo "# Testing intrepyd"
	@$(PYTHON) -m unittest discover -v

coverage_python:
	@echo "# Testing intrepyd"
	@$(PYTHON) -m coverage run -m unittest discover && \
		$(PYTHON) -m coverage report && $(PYTHON) -m coverage html

# 'setup.py install' was removed from setuptools; pip is the supported path
install_intrepyd: fetch_intrepid
	@echo "# Locally installing intrepyd"
	@$(PYTHON) -m pip install --user .

# The documentation site, built with MkDocs (see mkdocs.yml). The API
# reference is generated from the sources by mkdocstrings, so the site stays in
# sync with the code and nothing generated is committed. The 'docs' dependency
# group installs what it needs (make install_dev, or pip install --group docs).
build_docs:
	@echo "# Build the documentation site into site/"
	@$(PYTHON) -m mkdocs build --strict

# Preview the site locally at http://127.0.0.1:8000, rebuilding on every change
serve_docs:
	@$(PYTHON) -m mkdocs serve

# A wheel holds the library of one platform, and works with any python 3 on
# it. Releases build them in CI (see release below); these targets are for
# trying them out.
wheel: fetch_intrepid
	@echo "# Building the wheel for $$(cat .intrepid/PLATFORM)"
	@rm -fr build intrepyd.egg-info
	@$(PYTHON) -m build --wheel --outdir dist
	@rm -fr build intrepyd.egg-info

wheels:
	@rm -fr dist
	@for platform in linux-x86_64 windows-x86_64; do \
		$(MAKE) --no-print-directory wheel PLATFORM=$$platform || exit 1; \
	done
	@$(MAKE) --no-print-directory fetch_intrepid

# Tags the current commit as v$(VERSION) and pushes the tag, which starts the
# release workflow, .github/workflows/release.yml: it tests, builds the wheels
# of every platform, checks them, publishes them on PyPI and makes a GitHub
# release. The commit must already be on $(REMOTE)/$(BRANCH); VERSION must be
# later than every version on PyPI, and have a section in CHANGELOG.md; the
# intrepid release in INTREPID_VERSION must exist.
release:
	@test -z "$$(git status --porcelain)" || \
		{ echo "Error: the working tree has uncommitted changes"; exit 1; }
	@test "$$(git rev-parse --abbrev-ref HEAD)" = "$(BRANCH)" || \
		{ echo "Error: releases are made from $(BRANCH), not $$(git rev-parse --abbrev-ref HEAD)"; exit 1; }
	@$(PYTHON) tools/check_release.py check
	@gh release view "v$(INTREPID_VERSION)" -R $(INTREPID_REPO) --json tagName >/dev/null 2>&1 || \
		{ echo "Error: cannot find release v$(INTREPID_VERSION) of $(INTREPID_REPO) (is gh installed and logged in?)"; exit 1; }
	@git fetch --quiet --tags $(REMOTE) $(BRANCH) 2>/dev/null || \
		{ echo "Error: cannot fetch $(BRANCH) from $(REMOTE): push it first"; exit 1; }
	@test "$$(git rev-parse HEAD)" = "$$(git rev-parse $(REMOTE)/$(BRANCH))" || \
		{ echo "Error: HEAD is not $(REMOTE)/$(BRANCH): push or pull first"; exit 1; }
	@! git rev-parse --quiet --verify "refs/tags/v$(VERSION)" >/dev/null || \
		{ echo "Error: v$(VERSION) already exists: bump VERSION"; exit 1; }
	@git tag -a "v$(VERSION)" -m "intrepyd $(VERSION)"
	@git push $(REMOTE) "refs/tags/v$(VERSION)"
	@echo "# Pushed v$(VERSION): the CI now tests, builds and publishes the release"

# Deletes the tag v$(VERSION), locally and on $(REMOTE), so that 'make release'
# can tag again, e.g. after a fix to a release whose CI failed. It refuses once
# PyPI has v$(VERSION): PyPI never takes a version twice, so bump VERSION.
undorelease:
	@$(PYTHON) tools/check_release.py published; status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo "Error: intrepyd $(VERSION) is already on PyPI: bump VERSION instead"; exit 1; \
	elif [ $$status -ne 1 ]; then exit 1; fi
	@git fetch --quiet --tags $(REMOTE) 2>/dev/null || true
	@local=$$(git rev-parse --quiet --verify "refs/tags/v$(VERSION)^{commit}"); \
	remote=$$(git ls-remote --tags $(REMOTE) "refs/tags/v$(VERSION)"); \
	if [ -z "$$local$$remote" ]; then echo "Error: there is no tag v$(VERSION)"; exit 1; fi; \
	if [ -n "$$local" ]; then echo "v$(VERSION) points to: $$(git log -1 --format='%h %s' $$local)"; fi; \
	printf "Delete v$(VERSION) locally and on $(REMOTE)? [y/N] "; read answer; \
	[ "$$answer" = y ] || [ "$$answer" = Y ] || { echo "Nothing deleted"; exit 1; }; \
	if [ -n "$$local" ]; then git tag -d "v$(VERSION)"; fi; \
	if [ -n "$$remote" ]; then git push $(REMOTE) ":refs/tags/v$(VERSION)"; fi
	@echo "# Deleted v$(VERSION): fix, commit, push, then run 'make release' again"
