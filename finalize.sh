#!/usr/bin/env bash
# Safe export: explicit approved source; no deletion, auto-pick, or overwrite.
# bash finalize.sh job --source approved-cut.mp4                 # verify only
# bash finalize.sh job --source approved-cut.mp4 --approved --apply
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if python3 -c 'import sys; assert sys.version_info >= (3,9)' >/dev/null 2>&1; then PYBIN=python3
elif python -c 'import sys; assert sys.version_info >= (3,9)' >/dev/null 2>&1; then PYBIN=python
else echo 'Necesitas Python 3.9 o superior. Ejecuta check-setup.sh.' >&2; exit 1; fi
exec "$PYBIN" "$ROOT/workflows/finalize-safe.py" "$@"
