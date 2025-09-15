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

# Lint the code
lint:
  uv run $uv_flags ruff check

# Run static checks
static:
  uv run $uv_flags pyright

alias fmt := format
# Format the code
format:
  uv run $uv_flags ruff check --fix-only

# Run all tests
test: lint static unit solution doctest

# Run unit tests
unit *args='':
  uv run $uv_flags coverage run --source=src/juju_doctor -m pytest "${args:-tests/unit}"
  uv run $uv_flags coverage report
  
# Run solution tests
solution *args='':
  uv run $uv_flags coverage run --source=src/juju_doctor -m pytest "${args:-tests/solution}"
  uv run $uv_flags coverage report

# TODO: I need to test with all env vars enabled in CI YAML, it is assumed locally that user has:
# - uv sync --extra=dev && source .venv/bin/activate
# Make a doc out of THIS

doctest: doctest-builtin doctest-examples

# Run doctests on example COS probes
[working-directory("./examples")]
doctest-examples:
  #!/usr/bin/env sh
  for file in *.py; do
    python3 -m doctest "$file" || exit 1
  done
  echo "{{BOLD + GREEN}}SUCCESS: All COS probe tests passed!"

# Run doctests on builtin COS probes
doctest-builtin:
  #!/usr/bin/env sh
  for file in ./src/juju_doctor/builtin/*.py; do
    python3 -m doctest "$file" || exit 1
  done
  echo "{{BOLD + GREEN}}SUCCESS: All builtin probe tests passed!"

# Lint the schema to ensure it is updated
schema:
  just schema-diff ruleset
  just schema-diff builtins

schema-diff *type:
  #!/usr/bin/env bash
  uv sync --extra=dev > /dev/null 2>&1
  source .venv/bin/activate
  echo $1
  if ! diff <(juju-doctor schema --{{type}}) schema/{{type}}.json; then
    exit 1
  fi
