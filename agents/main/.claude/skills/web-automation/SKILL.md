---
name: Web Automation
description: Drive a real browser — open pages, click, type, fill forms, screenshot. Assigning this skill grants the web tool.
---

You can operate a REAL web browser through the 'web' MCP tool (Playwright).
Be fast and deliberate — don't over-explore or narrate every step:
1. browser_navigate to the URL, then browser_snapshot to SEE the page as a
   structured accessibility tree with refs — act on those refs, don't guess CSS
   selectors. Re-snapshot after the page changes (navigation, submit, AJAX).
2. Interact via browser_click / browser_type / browser_select_option /
   browser_fill_form using the element ref from the latest snapshot.
3. Show the owner progress with browser_take_screenshot at key steps; for plain
   reading, the snapshot text is enough — screenshot when layout/visuals matter.
Visible vs background: the 'web' tool opens a VISIBLE browser the owner can watch
in real time. If the owner wants it done quietly, use the 'web-bg' tool instead
(identical abilities, no window). Pick the one that matches what the owner asked.
Safety: it runs in a fresh profile that is NOT logged in. Never type the owner's
real credentials, never buy or do destructive/irreversible actions without explicit
confirmation, and stay on the task's site(s).
