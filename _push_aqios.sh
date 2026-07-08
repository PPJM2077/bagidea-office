#!/bin/bash
set -e
cd /c/Users/johnw/AppData/Local/BagIdeaOffice/app

# Stage all plugin source files (excluding data/)
find plugins -maxdepth 2 -type f -not -path "*/data/*" -exec git add -f {} +

# Stage docs and package
git add -f docs/ai-quant-office/
git add -f workspace/ai-plugin-package/
git add -f .gitignore

# Show count
echo "=== Staged files ==="
git diff --cached --name-only | wc -l

# Commit
git commit -m "feat: AQIOS v1.0.0 — 14 plugins, 73 commands, full AI Office OS

- 14 AQIOS plugins: ai-employee, ai-gateway, architecture-gate,
  company-dashboard, company-governance, execution-engine, knowledge-os,
  market-regime, portfolio-mm, research-engine, risk-monitor,
  strategy-engine, task-system, tech-decision
- docs/ai-quant-office/: 10-book specification
- workspace/ai-plugin-package/: AI-native package (7 files)
- .gitignore: track plugin source, ignore runtime data/

Co-Authored-By: Claude <noreply@anthropic.com"

echo "=== Commit done ==="

# Push
git push origin main
echo "=== Push done ==="
