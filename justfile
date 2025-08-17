set export  # Just variables are exported to environment variable

uv := `which uv`
uv_flags := "--frozen --isolated --extra=dev"
PYTHONPATH := "src/juju_doctor"

[private]
default:
  just --list

# Update uv.lock with the latest deps
lock:
  uv lock --upgrade --no-cache

# Run all tests
test: lint static unit solution

# Lint the code
lint:
  uv run $uv_flags ruff check

# Lint the schema file to ensure it is updated
lint-schema:
  #!/bin/bash
  uv sync --extra=dev && source .venv/bin/activate
  uv pip install -e .
  juju-doctor schema --output tmp/schema/ruleset.json
  diff tmp/schema/ruleset.json schema/ruleset.json

# Run static checks
static:
  uv run $uv_flags pyright

alias fmt := format
# Format the code
format:
  uv run $uv_flags ruff check --fix-only

# Run unit tests
unit *args='':
  uv run $uv_flags coverage run --source=src/juju_doctor -m pytest "${args:-tests/unit}"
  uv run $uv_flags coverage report
  
# Run solution tests
solution *args='':
  uv run $uv_flags coverage run --source=src/juju_doctor -m pytest "${args:-tests/solution}"
  uv run $uv_flags coverage report
