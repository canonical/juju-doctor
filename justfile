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

doctest: doctest-builtin doctest-examples

# Run doctests on example COS probes
[working-directory("./examples")]
doctest-examples:
  #!/usr/bin/env sh
  for file in *.py; do
    python3 -m doctest "$file" || exit 1
  done
  echo "SUCCESS: All example probe tests passed!"

# Run doctests on builtin COS probes
doctest-builtin:
  #!/usr/bin/env sh
  for file in ./src/juju_doctor/builtin/*.py; do
    python3 -m doctest "$file" || exit 1
  done
  echo "SUCCESS: All builtin probe tests passed!"
