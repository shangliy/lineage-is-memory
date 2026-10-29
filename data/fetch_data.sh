#!/usr/bin/env bash
# Download the public benchmarks into data/public and check them against SHA256SUMS.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p public/banking77 public/bbh
B=https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data
for f in train test; do [ -s public/banking77/$f.csv ] || curl -sfL -o public/banking77/$f.csv $B/$f.csv; done
f=salient_translation_error_detection.json
[ -s public/bbh/$f ] || curl -sfL -o public/bbh/$f https://raw.githubusercontent.com/suzgun/BIG-Bench-Hard/main/bbh/$f
(cd public && sha256sum -c ../SHA256SUMS)
echo "export PUBLIC_DATA_DIR=$PWD/public"
