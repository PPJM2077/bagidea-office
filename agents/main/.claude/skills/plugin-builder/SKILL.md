---
name: Plugin Builder
description: Build, deploy, and update an office plugin — end to end.
---

To build OR update an office plugin (full spec: docs/guide/plugins.md):
1. plugins/<id>/plugin.json (id, name, description, panel?, commands[]). START the
   name with an emoji — that emoji is the plugin's icon in the Plugins panel.
2. Add index.js exporting (ctx) => ({ onCommand?, routes? }) for server logic;
   ctx gives broadcast, feed, reg, runClaude, dataDir, pluginDir and more.
3. Add panel.html for a UI (dark theme #0c1322 / #5ec8ff; slim scrollbar).
   It can pop out into its OWN resizable window (⤢) — keep the layout fluid
   (%/vh/flex, not fixed px) and set window:{w,h,resizable} in plugin.json.
4. Keep private state in ctx.dataDir; broadcast {type:'plugin.event',plugin:'<id>'}.
5. DEPLOY — the office ONLY runs plugins from plugins/<id>/. If you developed or
   edited the plugin ANYWHERE ELSE (a workspace project, a dev mirror, a clone),
   copy the changed files INTO plugins/<id>/ — but NEVER overwrite its data/ dir
   (user state / keys) or node_modules. Building it elsewhere does NOT make it run.
6. Reload: curl -s -X POST http://127.0.0.1:8787/plugins/reload -H 'x-bagidea-ui: 1'.
7. VERIFY it took effect — the job is NOT done until the RUNNING office reflects it:
   GET /plugins must show your plugin at the NEW version (not a stale old one), and
   the daemon log shows '[plugin] loaded <id> v<new>' with no 'load fail'. Only then
   is it deployed. Then POST /plugin/<id>/cmd to confirm behavior. (Publishing to a
   git repo / the Hub is a separate, owner-approved step — never assumed.)
Mirror the music/calculator plugins.
