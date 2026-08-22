# Usage:
#   make install          # deps for dev
#   make install-all      # deps for all groups
#   make lint             # static checks (no writes)
# 	make lint-fix		  # lint + fix
#   make format           # auto-format files in-place
#   make fmt-check        # verify formatting only
#   make test             # run tests
#   make ci               # lint + fmt-check + test
#   make clean            # remove caches/artifacts
#   make lock             # (re)solve and update lockfile
#   make help             # this help

SHELL := /bin/bash
.ONESHELL:
.IGNORE: clean
.DEFAULT_GOAL := help

PY ?= python
UV ?= uv
RUFF ?= ruff
MYPY ?= mypy

CODE := src
TESTS := tests

.PHONY: install install-all lint format fmt-check test ci lock clean typing help

# -------- Tasks --------

install: ## Sync runtime + dev dependencies
	$(UV) venv --seed
	$(UV) sync --group dev

install-all: ## Sync all dependency groups
	$(UV) sync --all-groups

lint: ## Lint (no writes)
	$(UV) run $(RUFF) check $(CODE) $(TESTS)

lint-fix: ## Lint and fix
	$(UV) run $(RUFF) check $(CODE) $(TESTS) --fix

format: ## Auto-format code
	$(UV) run $(RUFF) format $(CODE)
	$(UV) run $(RUFF) format $(TESTS)

fmt-check: ## Check formatting without writing
	$(UV) run $(RUFF) format --check $(CODE)

typing: ## Run the typing checks
	$(UV) run $(MYPY) $(CODE)

test: ## Run test suite
	$(UV) run pytest --cov=src --cov-fail-under=95 --cov-report term-missing --disable-warnings

ci: ## Lint + format check + tests (for CI pipelines)
	$(MAKE) lint
	$(MAKE) fmt-check
	$(MAKE) test

lock: ## Update lockfile (re-resolve)
	$(UV) lock

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info .mypy_cache

help: ## Show this help
	@grep -E '^[[:alnum:]_.-]+:.*## ' $(MAKEFILE_LIST) | \
	  sed -E 's/^([[:alnum:]_.-]+):[^#]*## (.*)/\t- \1 - \2/' | \
	  sort
