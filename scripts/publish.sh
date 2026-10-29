#!/usr/bin/env bash
# Build and verify the arXiv submission package (paper/arxiv-upload.tar.gz)
# and generate copy-paste submission metadata (paper/arxiv-metadata.txt).
#
# Usage:
#   bash scripts/publish.sh
#   EMAIL=kuoysl@gmail.com bash scripts/publish.sh   # optional email override

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPER_DIR="$ROOT/paper"
EMAIL_ADDR="${EMAIL:-kudoysl@gmail.com}"

echo "=== 1. Updating author email ($EMAIL_ADDR) and compiling paper/paper.tex ==="
cd "$PAPER_DIR"

# Ensure email in paper.tex matches EMAIL_ADDR
sed -i -E "s/\\\\texttt\\{[a-zA-Z0-9._%+-]+@gmail\\.com\\}/\\\\texttt{${EMAIL_ADDR}}/g" paper.tex

pdflatex -interaction=nonstopmode paper.tex >/dev/null
bibtex paper >/dev/null
pdflatex -interaction=nonstopmode paper.tex >/dev/null
pdflatex -interaction=nonstopmode paper.tex >/dev/null

echo "=== 2. Staging arXiv bundle and running isolated AutoTeX simulation ==="
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/figs"
cp "$PAPER_DIR/paper.tex" "$STAGE/paper.tex"
cp "$PAPER_DIR/paper.bbl" "$STAGE/paper.bbl"
cp "$PAPER_DIR/figs/fig1-lineage-disclosure.png" "$STAGE/figs/"
cp "$PAPER_DIR/figs/fig2-banking77-carry.png" "$STAGE/figs/"

# Package tarball BEFORE running test pdflatex so no .aux/.log/.pdf pollute the archive
OUT_TAR="$PAPER_DIR/arxiv-upload.tar.gz"
tar -czf "$OUT_TAR" -C "$STAGE" paper.tex paper.bbl figs/fig1-lineage-disclosure.png figs/fig2-banking77-carry.png

# Simulate arXiv's AutoTeX server (runs pdflatex on paper.tex + paper.bbl WITHOUT bibtex or refs.bib)
(
  cd "$STAGE"
  pdflatex -interaction=nonstopmode paper.tex >/dev/null
  pdflatex -interaction=nonstopmode paper.tex >/dev/null
  if grep -q "Citation .* undefined" paper.log; then
    echo "ERROR: Undefined citations in arXiv simulation!" >&2
    exit 1
  fi
  if grep -q "^! " paper.log; then
    echo "ERROR: LaTeX error in arXiv simulation!" >&2
    exit 1
  fi
)

PAGES="$(pdfinfo "$PAPER_DIR/paper.pdf" | awk '/^Pages:/ {print $2}')"
TAR_SIZE="$(du -h "$OUT_TAR" | cut -f1)"

META_FILE="$PAPER_DIR/arxiv-metadata.txt"
cat > "$META_FILE" <<EOF
========================================================================
arXiv Submission Metadata & Checklist (https://arxiv.org/submit)
========================================================================

1. Upload Package:
   File: $OUT_TAR ($TAR_SIZE)
   Contents:
     - paper.tex
     - paper.bbl
     - figs/fig1-lineage-disclosure.png
     - figs/fig2-banking77-carry.png

2. License:
   CC BY 4.0 (Creative Commons Attribution 4.0 International)

3. Categories:
   Primary Category:   cs.LG (Machine Learning)
   Cross-List:         cs.CL (Computation and Language), cs.AI (Artificial Intelligence), cs.SE (Software Engineering)

4. Title:
Lineage Is Memory: Parent Inheritance and Feedback Disclosure in Short-Budget LLM-Guided Optimization

5. Authors:
Shanglin Yang (Independent Researcher), Zhan Shi (Santa Clara University)

   - Author 1: Shanglin Yang
     Affiliation: Independent Researcher
     Email: $EMAIL_ADDR
   - Author 2: Zhan Shi
     Affiliation: Santa Clara University

6. Abstract (copy and paste directly into arXiv Abstract box):
Iterative language-model optimizers refine prompts and programs by evaluating a candidate, showing a proposer model a sample of failing cases, and keeping revisions that improve performance. Recent work attributes the limits of this loop to narrow single-round reflection, introducing full-set error clustering, targeted minibatches, or larger proposer models so the optimizer sees more failure modes per step. Yet every existing evaluation tests these mechanisms exclusively inside lineage-preserving search, where each revision edits a surviving parent, leaving the contribution of parent inheritance confounded with the breadth of per-round feedback. Across 1,750 pre-registered runs spanning nine prompt and program synthesis benchmarks, we separate parent inheritance from feedback disclosure under matched evaluation budgets. We find that greedy parent inheritance drives the vast majority of optimization progress, outperforming seed-reset resampling even when seed-reset proposals receive a clustered summary of all failures in every round or use a larger proposer model. While full-set error clustering and diverse failure selection improve single-step rewrites from the seed and accelerate the opening rounds of search, sequential parent inheritance rapidly closes this gap as solved error modes are retained in the candidate and filtered from subsequent failure lists. Moreover, decomposing token expenditure in GEPA reveals that proposer reflection accounts for only a small fraction of total cost whereas validation and minibatch gating consume nearly the entire budget, showing that greedy parent inheritance over raw failures captures the gains of complex reflective loops at a fraction of their compute.

7. Comments:
$PAGES pages, 2 figures, 10 tables. Code, pre-registrations, and 1,750 run logs at https://github.com/shangliy/lineage-is-memory
========================================================================
EOF

echo "=== 3. Done! ==="
echo "  PDF:      $PAPER_DIR/paper.pdf ($PAGES pages)"
echo "  Tarball:  $OUT_TAR ($TAR_SIZE)"
echo "  Metadata: $META_FILE"
echo "  Contents of $OUT_TAR:"
tar -ztvf "$OUT_TAR"
