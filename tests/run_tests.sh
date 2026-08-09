#!/usr/bin/env bash
# Runs the site test suite. Used directly, or by the pre-commit hook
# (see .githooks/pre-commit).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tests/test_site.py
