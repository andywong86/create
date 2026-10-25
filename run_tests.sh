#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

# Run all tests by default; forward arguments to allow selecting tests or options.
exec uv run --with pytest python -m pytest "$@"
