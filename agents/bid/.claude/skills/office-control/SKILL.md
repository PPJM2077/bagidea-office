---
name: Office Control
description: Drive the live office through its local HTTP API and plugins.
---

The office daemon runs at http://127.0.0.1:8787. Use Bash + curl to drive it:
- GET /registry  -> the current roster, roles, skills, settings (JSON).
- Plugins you can command appear in the <office-plugins> note in your prompt;
  call them with POST /plugin/<id>/cmd  -d '{"cmd":"...","args":"..."}'.
- To leave a note for the owner, append a '- <line>' to workspace/notes.md.
Read state before acting, make the smallest change that does the job, and
report exactly what you changed. Never call owner-only or destructive APIs.
