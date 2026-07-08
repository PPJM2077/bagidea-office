---
name: Debug Detective
description: Systematic root-cause hunting instead of guess-and-check.
---

When chasing a bug:
1. Reproduce it reliably first; capture the exact error and the steps.
2. Form a hypothesis, then read the code path top-down to confirm or kill it.
3. Add targeted logging / minimal probes; change ONE thing at a time.
4. Find the root cause, not just the symptom; check for the same bug elsewhere.
5. Fix it, prove the fix with a test or a clean repro, and explain the cause.
