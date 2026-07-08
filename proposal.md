# Proposal: Office-as-Plugin-Core (v2 — corrected)

**หลักการ:** ยึด BagIdea Office เป็นแกนหลัก ทุกฟีเจอร์ใหม่เกิดเป็น plugin ที่ agent สั่งได้
และ user เปิดเป็น panel ได้ — แทนที่จะฝังเป็นโมดูลภายในโปรเจค

**เหตุผลเชิงสถาปัตยกรรม:**
- ทั้ง `ai-quant-org-blueprint` และ `company-simulator` มี layer structure ชัดเจน
  (foundation / core / extensions / features / apps / plugins) + governance artifacts
  (architecture-review.md, ADRs, module.json × 15, module.schema.json)
- Plugin framework ของออฟฟิศรองรับครบ (per `docs/guide/plugins.md`):
  - **Manifest**: `plugin.json` กำหนด `id`, `name`, `version`, `description`, `panel`, `window`, `commands[]`, `needsKeys[]`, `enabled`
  - **Commands**: array ของ `{name, args, desc}` — inject เข้า agent prompt อัตโนมัติ
  - **Server**: `index.js` export `(ctx) => ({ onCommand, routes })` — จัดการ command + custom HTTP routes
  - **Panel**: `panel.html` เรียก `/plugin/<id>/cmd` (POST) + `/plugin/<id>/state` (GET) + WebSocket `ws://127.0.0.1:8787/ws` สำหรับ live updates
  - **Context**: `ctx.broadcast(event, persist?)`, `ctx.feed(text, agentId?)`, `ctx.reg`, `ctx.saveReg()`, `ctx.workspace`, `ctx.daemonDir`, `ctx.dataDir`, `ctx.pluginDir`, `ctx.manifest`, `ctx.log(msg)`, `ctx.runClaude(agentId, prompt, opts?)`
- Agent ทุกตัวในออฟฟิศเรียก command ของ plugin ได้ฟรีผ่าน:
  ```bash
  curl -s -X POST http://127.0.0.1:8787/plugin/<id>/cmd \
    -H "content-type: application/json" -d '{"cmd":"<name>","args":"<value>"}'
  ```

**เกณฑ์เลือก 3 ตัวนี้:**
1. ต้องดึงค่าจาก artifacts ที่มีอยู่แล้วในโปรเจคมาใช้ (ไม่ใช่สร้างใหม่จากศูนย์)
2. ต้องให้ agent สั่งงานได้จริง (ไม่ใช่แค่ dashboard อ่านอย่างเดียว)
3. ต้องขยายเป็น platform ได้ — โปรเจคอื่นในอนาคตเสียบต่อได้ทันที

---

## ตัวเลือกที่ 1: 📊 `company-dashboard` — หน้าจอสุขภาพโปรเจค

**plugin id:** `company-dashboard`
**ชื่อ:** 📊 Company Dashboard

**ทำไมคุ้ม:**
- `company-simulator/module.json` × 15 ไฟล์ + `architecture-review.md` + `docs/adr/*.md` (0000-0015 + TEMPLATE)
  มีข้อมูลสุขภาพสถาปัตยกรรมอยู่แล้ว แต่ต้องเปิด terminal / อ่านไฟล์เอง
- Plugin นี้ aggregate เป็น live cards — CEO เห็นภาพเดียวรู้สถานะทั้งหมด
- Agent เรียก `status` แล้วโพสต์สรุปเข้า feed ได้ทุกวัน (loop skill)

**Agent commands** (per plugin.json `commands[]` schema — each has `{name, args, desc}`):
- `status` — สรุปสุขภาพ (layer violations จาก `scripts/check-layer-boundary.py`, test pass rate, ADR compliance จาก `scripts/check-adr.py`)
- `layers` — สถานะแต่ละ layer (foundation/core/extensions/features/apps/plugins)
- `adr [list|show <id>]` — ดูรายการ ADR จาก `docs/adr/` และสถานะ (proposed/ratified/superseded)
- `gate` — ผล architecture gate ล่าสุด (6 CI gates จาก architecture-review.md §3 — รัน `scripts/validate-modules.py`, `scripts/check-*.py`)
- `modules` — รายชื่อ module จาก `module.json` × 15 + dependencies + owner

**Panel จะมี** (per `panel.html` spec — เรียก `/plugin/<id>/cmd` + WebSocket `ws://127.0.0.1:8787/ws` สำหรับ live updates):
- Card per layer: สีเขียว/เหลือง/แดง ตาม violation count (broadcast via `ctx.broadcast({type:"plugin.event", plugin:"company-dashboard", ...})`)
- ADR timeline (ratified dates, active vs superseded) — อ่านจาก `docs/adr/*.md`
- Recent commits + test trend sparkline
- Module dependency graph (interactive) — สร้างจาก `module.json` dependencies

**ไฟล์โปรเจคที่ใช้:**
- `company-simulator/module.json` (×15 — 15 modules รวม root)
- `company-simulator/architecture-review.md` (governance spec)
- `company-simulator/docs/adr/*.md` (0000-0015 + TEMPLATE.md)
- `company-simulator/scripts/check-adr.py`, `check-layer-boundary.py`, `validate-modules.py`, `check-api-surface.py`, `check-circular-imports.py`, `check-internal-imports.py` (architecture checkers)
- `company-simulator/tests/` (parse results)

---

## ตัวเลือกที่ 2: 🧭 `tech-decision` — Navigator สำหรับ technology decisions

**plugin id:** `tech-decision`
**ชื่อ:** 🧭 Tech Decision Navigator

**ทำไมคุ้ม:**
- `ai-quant-org-blueprint/analysis/` มี `01-org-structure.md`, `02-technology-providers.md`,
  `03-complete-blueprint.md`, `technology-decision-log.md` — เป็น static docs ที่กระจัดกระจาย
- Plugin รวมเป็น decision workbench: agent เรียก `providers` แล้วเทียบ tech stack,
  `decisions` แล้วดู decision log, `blueprint` แล้ว navigate architecture
- `GEMINI_API_KEY` มีอยู่ใน env แล้ว — plugin เรียก LLM วิเคราะห์ trade-offs ได้ทันที
- ขยายเป็น "decision tracker" สำหรับโปรเจคอื่นได้ (ทุกโปรเจคมี tech decisions)

**Agent commands** (per plugin.json `commands[]` schema):
- `decisions [list|show <id>]` — อ่าน `technology-decision-log.md` แสดง decision + rationale
- `providers [list|compare <name>]` — ดึง tech providers จาก `02-technology-providers.md`
- `blueprint [section]` — navigate `03-complete-blueprint.md` (org structure, modules, data flow)
- `org [show|roster]` — ดึง org structure จาก `01-org-structure.md` + `roster-check.json`
- `search <keyword>` — ค้นหาข้าม analysis docs ทั้งหมด (ใช้ `ctx.runClaude` สำหรับ semantic search)

**Panel จะมี** (per `panel.html` spec):
- Decision log viewer (render markdown พร้อม citations จาก `technology-decision-log.md`)
- Tech provider comparison table (จาก `02-technology-providers.md`)
- Blueprint navigator (section tree จาก `03-complete-blueprint.md`)
- Org chart (จาก `01-org-structure.md` + `roster-check.json`)
- Search box (semantic search ผ่าน `ctx.runClaude`)

**ไฟล์โปรเจคที่ใช้:**
- `ai-quant-org-blueprint/analysis/01-org-structure.md`
- `ai-quant-org-blueprint/analysis/02-technology-providers.md`
- `ai-quant-org-blueprint/analysis/03-complete-blueprint.md`
- `ai-quant-org-blueprint/analysis/technology-decision-log.md`
- `ai-quant-org-blueprint/analysis/roster-check.json`

---

## ตัวเลือกที่ 3: 🏛️ `architecture-gate` — ผู้พิทักษ์สถาปัตยกรรมข้ามโปรเจค

**plugin id:** `architecture-gate`
**ชื่อ:** 🏛️ Architecture Gate

**ทำไมคุ้ม:**
- `company-simulator` มี enforcement gate ครบแล้ว (6 CI gates, pre-push hooks,
  ADR workflow) — แต่ฝังอยู่ในโปรเจคเดียว
- Plugin นี้ **externalize** governance ออกมาเป็น office-level service
  → โปรเจคใหม่ในอนาคตเสียบต่อได้โดยไม่ต้องสร้าง gate เอง
- Agent เรียก `check` ก่อน commit ได้ (hook) หรือ `propose-adr` เริ่ม workflow
- Panel เป็น approval queue — CEO อนุมัติ ADR / layer violation exception ได้จากที่เดียว

**Agent commands** (per plugin.json `commands[]` schema):
- `check [project]` — รัน architecture check (layer violations จาก `scripts/check-layer-boundary.py`, ADR compliance จาก `scripts/check-adr.py`, module validation จาก `scripts/validate-modules.py`)
- `propose-adr <title>` — เริ่ม ADR workflow (สร้าง draft ใน `docs/adr/` จาก `TEMPLATE.md`)
- `review <adr-id>` — แสดง ADR สำหรับ review (อ่านจาก `docs/adr/<id>.md`)
- `approve <adr-id>` — อนุมัติ ADR (เปลี่ยนสถานะเป็น ratified, broadcast ผ่าน `ctx.broadcast`)
- `exceptions` — รายการ layer violation ที่ขอ exception (เก็บใน `ctx.dataDir`)
- `report` — สรุป governance status ทุกโปรเจค (aggregate จาก `ctx.reg.projects`)

**Panel จะมี** (per `panel.html` spec):
- Project selector (dropdown — อ่านจาก `ctx.reg.projects`)
- Violation log (filter by severity / layer / module) — ผลจาก `scripts/check-*.py`
- ADR queue (proposed → reviewing → ratified / rejected) — อ่านจาก `docs/adr/*.md`
- Exception request queue (with justification + approver) — เก็บใน `ctx.dataDir`
- Cross-project governance heatmap (broadcast live ผ่าน WebSocket)

**ไฟล์โปรเจคที่ใช้:**
- `company-simulator/architecture-review.md` (governance spec — 6 CI gates)
- `company-simulator/module.schema.json` (validation rules สำหรับ `scripts/validate-modules.py`)
- `company-simulator/docs/adr/` (0000-0015 + TEMPLATE.md — ADR templates + history)
- `company-simulator/scripts/check-adr.py`, `check-layer-boundary.py`, `validate-modules.py`, `check-api-surface.py`, `check-circular-imports.py`, `check-internal-imports.py` (architecture checkers)
- `company-simulator/.github/workflows/validate.yml` (CI gate logic)
- `company-simulator/.husky/` (pre-push hooks)

---

## สรุปเปรียบเทียบ

| มิติ | 📊 company-dashboard | 🧭 tech-decision | 🏛️ architecture-gate |
|---|---|---|---|
| **ความคุ้ม** | สูง — ใช้ของที่มีทันที | สูง — รวม scattered docs เป็น workbench | สูงมาก — ป้องกัน system chaos ข้ามโปรเจค |
| **ความยาก** | ปานกลาง (read-only aggregate) | ปานกลาง (parse markdown + semantic search) | ปานกลาง (externalize existing gate) |
| **Agent value** | รายงานอัตโนมัติ (loop skill) | วิจัย + ตัดสินใจ (ใช้ `ctx.runClaude`) | บังคับใช้ governance (pre-commit hook) |
| **ขยายได้** | ทุกโปรเจคที่มี module.json | ทุกโปรเจคที่มี tech decisions | ทุกโปรเจคที่ต้องการ governance |
| **CEO เห็นค่า** | ทันที (health at a glance) | ชัด (decision traceability) | ชัด (ป้องกัน technical debt) |

**คำแนะนำ:** ถ้าต้องเลือกเดียว → เริ่มที่ **📊 company-dashboard** เพราะ:
1. ใช้ artifacts ที่มีอยู่แล้ว 100% (ไม่ต้องสร้างข้อมูลใหม่)
2. agent เรียก `status` แล้วโพสต์ feed ได้ทันที (proof of value เร็ว)
3. เป็น foundation สำหรับอีก 2 ตัว — dashboard แสดง health, tech-decision แสดง rationale,
   architecture-gate แสดง compliance — ทั้งสามเป็น "views" ของข้อมูลเดียวกัน

ถ้า CEO เห็นค่าของ plugin model → ค่อยต่อยอดอีก 2 ตัวเป็น phase 2/3

---

## Plugin Implementation Checklist (per docs/guide/plugins.md §8)

สำหรับแต่ละ plugin ที่เลือก ต้องมี:
- [ ] `plugin.json` with unique `id`, `name`, `description`, `commands[]` (each with `{name, args, desc}`)
- [ ] `index.js` exporting `(ctx) => ({ onCommand(cmd, args, reply), routes? })`
- [ ] `panel.html` สำหรับ UI (เรียก `/plugin/<id>/cmd` + WebSocket `ws://127.0.0.1:8787/ws`)
- [ ] commands listed in manifest so agents can use them (inject เข้า agent prompt อัตโนมัติ)
- [ ] private state ใน `ctx.dataDir` (ไม่ใช่ hard-coded paths)
- [ ] broadcast `plugin.event` ผ่าน `ctx.broadcast()` so open panels stay live
- [ ] test: `POST /plugin/<id>/cmd` returns what you expect
- [ ] reload: `curl -s -X POST http://127.0.0.1:8787/plugins/reload -H "x-bagidea-ui: 1"`
