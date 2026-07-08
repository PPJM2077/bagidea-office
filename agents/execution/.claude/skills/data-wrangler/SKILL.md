---
name: Data Wrangler
description: Parse, clean and transform CSV/JSON safely with small scripts.
---

When working with data files:
1. Inspect the shape first (columns, types, row count, encoding) before transforming.
2. Write a small, re-runnable script (node/python) — never hand-edit large files.
3. Validate: handle missing values, dedupe, and check totals against the source.
4. Keep the raw input untouched; write outputs to a new file.
5. Report row counts in vs out and any rows you dropped and why.
