#!/usr/bin/env bash
# Test koşucusu. Birim: saf mantık. --live: gerçek PipeWire grafı + kulaklık (headful kabul testleri).
set -uo pipefail
cd "$(dirname "$0")/.."
rc=0
echo "== UNIT"
python3 -m unittest discover -s tests -p 'test_*.py' -v 2>&1 | tail -n +1 || rc=1
python3 -m unittest discover -s tests -p 'test_*.py' >/dev/null 2>&1 || rc=1
echo "== UI (başsız, ses kapalı)"
python3 -m unittest discover -s tests/ui -p 'test_*.py' 2>&1 | tail -3 || rc=1
python3 -m unittest discover -s tests/ui -p 'test_*.py' >/dev/null 2>&1 || rc=1
if [ "${1:-}" = "--live" ]; then
  echo "== LIVE"
  python3 -m unittest discover -s tests/live -p 'test_*.py' -v 2>&1 || rc=1
fi
echo "== RESULT rc=$rc"
exit $rc
