# Configuration
# Determine this makefile's path.
# Be sure to place this BEFORE `include` directives, if any.
THIS_FILE := $(lastword $(MAKEFILE_LIST))
APP_ROOT := $(abspath $(lastword $(MAKEFILE_LIST))/..)
APP_NAME := raven-wps

WPS_URL := http://0.0.0.0:9099

GDAL_VERSION := $(shell gdal-config --version)

# Used in target refresh-notebooks to make it looks like the notebooks have
# been refreshed from the production server below instead of from the local dev
# instance so the notebooks can also be used as tutorial notebooks.
OUTPUT_URL = https://pavics.ouranos.ca/wpsoutputs

SANITIZE_FILE := https://github.com/Ouranosinc/PAVICS-e2e-workflow-tests/raw/master/notebooks/output-sanitize.cfg

ANACONDA_HOME := $(shell conda info --base 2> /dev/null)

ifeq "$(ANACONDA_HOME)" ""
ANACONDA_HOME := $(HOME)/miniconda3
endif

CONDA := $(shell command -v conda 2> /dev/null)
CONDA_ENV ?= $(APP_NAME)
PYTHON_VERSION = 3.6

# Choose Anaconda installer depending on your OS
ANACONDA_URL = https://repo.anaconda.com/miniconda
UNAME_S := $(shell uname -s)
DOWNLOAD_CACHE = /tmp/

# Additional servers used by notebooks
FLYINGPIGEON_WPS_URL = https://pavics.ouranos.ca/twitcher/ows/proxy/flyingpigeon/wps
FINCH_WPS_URL = https://pavics.ouranos.ca/twitcher/ows/proxy/finch/wps

# To run tests on local servers, use
# make FLYINGPIGEON_WPS_URL=http://localhost:8093 FINCH_WPS_URL=http://localhost:5000 test-notebooks

ifeq "$(UNAME_S)" "Linux"
FN := Miniconda3-latest-Linux-x86_64.sh
else ifeq "$(UNAME_S)" "Darwin"
FN := Miniconda3-latest-MacOSX-x86_64.sh
else
FN := unknown
endif

# end of configuration

.DEFAULT_GOAL := help

.PHONY: all
all: help

.PHONY: help
help:
	@echo "Please use 'make <target>' where <target> is one of:"
	@echo "  help              to print this help message. (Default)"
	@echo "  install           to install app by running 'pip install -e .'"
	@echo "  develop           to install with additional development requirements."
	@echo "  start             to start $(APP_NAME) service as daemon (background process)."
	@echo "  stop              to stop $(APP_NAME) service."
	@echo "  restart           to restart $(APP_NAME) service."
	@echo "  status            to show status of $(APP_NAME) service."
	@echo "  clean             to remove all files generated by build and tests."
	@echo "\nTesting targets:"
	@echo "  test              to run tests (but skip long running tests)."
	@echo "  test-all          to run all tests (including long running tests)."
	@echo "  test-notebooks    to verify Jupyter Notebook test outputs are valid."
	@echo "  lint              to run code style checks with flake8."
	@echo "  refresh-notebooks to verify Jupyter Notebook test outputs are valid."
	@echo "  pep8              to run pep8 code style checks."
	@echo "\nSphinx targets:"
	@echo "  docs              to generate HTML documentation with Sphinx."
	@echo "\nDeployment targets:"
	@echo "  dist              to build source and wheel package."

## Anaconda targets

.PHONY: anaconda
anaconda:
	@echo "Installing Anaconda ..."
	test -e $(ANACONDA_HOME)/bin/conda || curl $(ANACONDA_URL)/$(FN) --silent --insecure --output "$(DOWNLOAD_CACHE)/$(FN)"
	test -e $(ANACONDA_HOME)/bin/conda || bash "$(DOWNLOAD_CACHE)/$(FN)" -b -p $(ANACONDA_HOME)

.PHONY: conda_env
conda_env:
	@echo "Updating conda environment $(CONDA_ENV) ..."
	"$(ANACONDA_HOME)/bin/conda" create --yes -n $(CONDA_ENV) python=$(PYTHON_VERSION)
	"$(ANACONDA_HOME)/bin/conda" env update -n $(CONDA_ENV) -f environment.yml

.PHONY: env_clean
env_clean:
	@echo "Removing conda env $(CONDA_ENV)"
	@-"$(CONDA)" env remove -n $(CONDA_ENV) --yes

## Build targets

.PHONY: bootstrap
bootstrap: anaconda conda_env bootstrap_dev
	@echo "Bootstrap ..."

.PHONY: bootstrap_dev
bootstrap_dev:
	@echo "Installing development requirements for tests and docs ..."
	bash -c "source $(ANACONDA_HOME)/bin/activate $(CONDA_ENV) && pip install -r requirements_dev.txt"

.PHONY: install_ravenpy_with_binaries
install_ravenpy_with_binaries:
	# NOTE: this target should not be needed anymore since ravenpy can be
	# installed by conda and all the required binaries comes with it.
	# Have to uninstall first, otherwise ravenpy is already installed
	# without option "--with-binaries" so it won't re-install again, even
	# with "pip install --upgrade" because same version.
	bash -c 'pip uninstall --yes ravenpy'
	bash -c "pip install --no-cache-dir ravenpy[gis] gdal==$(GDAL_VERSION)"
	bash -c 'pip install ravenpy --install-option="--with-binaries"'

.PHONY: install
install:
	@echo "Installing application ..."
	@-bash -c 'pip install -e .'
	@echo "Start service with \`make start\`"

.PHONY: develop
develop:
	@echo "Installing development requirements for tests and docs ..."
	@-bash -c 'pip install -e ".[dev]"'

.PHONY: start
start:
	@echo "Starting application ..."
	@-bash -c "$(APP_NAME) start -d"

.PHONY: stop
stop:
	@echo "Stopping application ..."
	@-bash -c "$(APP_NAME) stop"

.PHONY: restart
restart: stop start
	@echo "Restarting application ..."

.PHONY: status
status:
	@echo "Showing status ..."
	@-bash -c "$(APP_NAME) status"

.PHONY: clean
clean: clean-build clean-pyc clean-test raven_clean ostrich_clean ## remove all build, test, coverage and Python artifacts

.PHONY: clean-build
clean-build:
	@echo "Removing build artifacts ..."
	@-rm -fr build/
	@-rm -fr dist/
	@-rm -fr .eggs/
	@-find . -name '*.egg-info' -exec rm -fr {} +
	@-find . -name '*.egg' -exec rm -f {} +
	@-find . -name '*.log' -exec rm -fr {} +
	@-find . -name '*.sqlite' -exec rm -fr {} +

.PHONY: clean-pyc
clean-pyc:
	@echo "Removing Python file artifacts ..."
	@-find . -name '*.pyc' -exec rm -f {} +
	@-find . -name '*.pyo' -exec rm -f {} +
	@-find . -name '*~' -exec rm -f {} +
	@-find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	@echo "Removing test artifacts ..."
	@-rm -fr .pytest_cache

.PHONY: clean-dist
clean-dist: clean
	@echo "Running 'git clean' ..."
	@git diff --quiet HEAD || echo "There are uncommitted changes! Aborting 'git clean' ..."
	## do not use git clean -e/--exclude here, add them to .gitignore instead
	@-git clean -dfx

## Test targets

.PHONY: test
test:
	@echo "Running tests (skip slow and online tests) ..."
	@bash -c "pytest -v -m 'not slow and not online' tests/"

.PHONY: test-all
test-all:
	@echo "Running all tests (including slow and online tests) ..."
	@bash -c "pytest -v tests/"

.PHONY: notebook-sanitizer
notebook-sanitizer:
	@echo "Copying notebook output sanitizer ..."
	@-bash -c "curl -L $(SANITIZE_FILE) -o $(CURDIR)/docs/source/output-sanitize.cfg --silent"

# Test all notebooks.
.PHONY: test-notebooks
test-notebooks: notebook-sanitizer
	@echo "Running notebook-based tests"
	@$(MAKE) -f $(THIS_FILE) test-notebooks-impl

# Test one single notebook (add .run at the end of notebook path).
# Might require one time `make notebook-sanitizer`.
%.ipynb.run: %.ipynb
	@echo "Testing notebook $<"
	@$(MAKE) -f $(THIS_FILE) test-notebooks-impl NB_FILE="$<"

NB_FILE := $(CURDIR)/docs/source/notebooks/
.PHONY: test-notebooks-impl
test-notebooks-impl:
	bash -c "env WPS_URL=$(WPS_URL) FINCH_WPS_URL=$(FINCH_WPS_URL) FLYINGPIGEON_WPS_URL=$(FLYINGPIGEON_WPS_URL) pytest --nbval-lax --verbose $(NB_FILE) --sanitize-with $(CURDIR)/docs/source/output-sanitize.cfg --ignore $(CURDIR)/docs/source/notebooks/.ipynb_checkpoints"

ifeq "$(JUPYTER_NB_IP)" ""
JUPYTER_NB_IP := 0.0.0.0
endif
.PHONY: notebook
notebook:
	@echo "Running notebook server"
	@bash -c "env WPS_URL=$(WPS_URL) FINCH_WPS_URL=$(FINCH_WPS_URL) FLYINGPIGEON_WPS_URL=$(FLYINGPIGEON_WPS_URL) jupyter notebook --ip=$(JUPYTER_NB_IP) $(CURDIR)/docs/source/notebooks/"

.PHONY: lint
lint:
	@echo "Running flake8 code style checks ..."
	@bash -c 'flake8 raven tests'

# Only works for notebooks that passed ``make test-notebooks`` above.  For
# those that failed, manually starting a local Jupyter server and refresh them
# manually.
.PHONY: refresh-notebooks
refresh-notebooks:
	@echo "Refresh all notebook outputs under docs/source/notebooks"
	bash -c 'for nb in $(CURDIR)/docs/source/notebooks/*.ipynb; do $(MAKE) -f $(THIS_FILE) refresh-notebooks-impl NB_REFRESH_FILE="$$nb"; done; cd $(APP_ROOT)'

# refresh one single notebook (add .refresh at the end of notebook path).
%.ipynb.refresh: %.ipynb
	@echo "Refreshing notebook $<"
	@$(MAKE) -f $(THIS_FILE) refresh-notebooks-impl NB_REFRESH_FILE="$<"

NB_REFRESH_FILE := ""
.PHONY: refresh-notebooks-impl
refresh-notebooks-impl:
	bash -c 'WPS_URL="$(WPS_URL)" FINCH_WPS_URL="$(FINCH_WPS_URL)" FLYINGPIGEON_WPS_URL="$(FLYINGPIGEON_WPS_URL)" jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=240 --output "$(NB_REFRESH_FILE)" "$(NB_REFRESH_FILE)"; sed -i "s@$(WPS_URL)/outputs/@$(OUTPUT_URL)/@g" "$(NB_REFRESH_FILE)"'

.PHONY: test_pdb
test_pdb:
	@echo "Running tests (skip slow and online tests) with --pdb ..."
	@bash -c "pytest -v -m 'not slow and not online' --pdb"

## Sphinx targets

.PHONY: docs
docs:
	@echo "Generating docs with Sphinx ..."
	@bash -c '$(MAKE) -C $@ clean html'
	@echo "Open your browser to: file:/$(APP_ROOT)/docs/build/html/index.html"
	## do not execute xdg-open automatically since it hangs travis and job does not complete
	@echo "xdg-open $(APP_ROOT)/docs/build/html/index.html"

## Deployment targets

.PHONY: dist
dist: clean
	@echo "Building source and wheel package ..."
	@-python setup.py sdist
	@-python setup.py bdist_wheel
	@-bash -c 'ls -l dist/'
