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
FETCH_ARGS=$(if $(INTREPID_DIR),--from $(INTREPID_DIR),) \
           $(if $(PLATFORM),--platform $(PLATFORM),)

all: fetch_intrepid all_linters all_tests

all_linters: linter_python

all_tests: tests_python

bootstrap_linux:
	@sudo apt update && sudo apt install -y make git python3-venv python3-pip
	@$(HOST_PYTHON) -m venv venv
	@./venv/bin/pip install -r requirements.txt
	@echo '*** Activate the virtualenv with: source venv/bin/activate ***'
	@echo '*** Add the following to your shell rc e.g., .zshrc ***'
	@echo 'export PYTHONPATH="$(CURDIR):$$PYTHONPATH"'

fetch_intrepid:
	@$(PYTHON) fetch_intrepid.py $(FETCH_ARGS)

# Fails if the score drops below fail-under in .pylintrc
linter_python:
	@$(PYTHON) -m pylint intrepyd

tests_python:
	@echo "# Testing intrepyd and apis"
	@$(PYTHON) -m unittest discover -v

coverage_python:
	@echo "# Testing intrepyd and apis"
	@$(PYTHON) -m coverage run -m unittest discover && \
		$(PYTHON) -m coverage report && $(PYTHON) -m coverage html

# 'setup.py install' was removed from setuptools; pip is the supported path
install_intrepyd:
	@echo "# Locally installing intrepyd"
	@$(PYTHON) -m pip install --user .

build_docs:
	@echo "# Generate docs"
	@[ -d docs ] || mkdir docs
	@$(PYTHON) -m pdoc3 -f -o docs intrepyd
	@rm -fr docs/intrepyd/tests

# A wheel holds the library of one platform, and works with any python 3 on
# it. Build one per platform, then upload them all with release_intrepyd_pip.
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

release_intrepyd_pip: wheels
	@echo "# Uploading intrepyd"
	@twine upload --repository pypi dist/*
