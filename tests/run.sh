#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -v -s . -p 'test_*.py'
