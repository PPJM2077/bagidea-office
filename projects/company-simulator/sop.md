# Standard Operating Procedures (SOP)

> ฉบับที่ 1 — มีผลบังคับใช้ทันที
> Owner: COO

---

## SOP-001: การรับคำสั่งจาก CEO

**วัตถุประสงค์:** ไม่ให้งานหลุดหรือถูกลืม

**ขั้นตอน:**

1. เมื่อ CEO ส่งงานมา — **ตอบรับทันที** ด้วยการสรุปความเข้าใจสั้นๆ
2. ถ้างานไม่ชัดเจน — ถามกลับให้ชัดก่อนรับ:
   - "ต้องการให้ทำอะไร"
   - "วัดผลสำเร็จยังไง"
   - " priority เท่าไหร่"
3. สร้าง Task ใน Task List (`TaskCreate`) ด้วยข้อมูล:
   - subject: ชื่องาน
   - description: requirement + criteria + priority
4. ถ้าสามารถเริ่มได้ทันที → เข้า SOP-002
5. ถ้าต้องรออะไร → ตั้ง blocker และแจ้ง CEO

**Checklist:**
- [ ] เข้าใจ requirement
- [ ] มีเกณฑ์สำเร็จ
- [ ] Task ถูกสร้างในระบบ
- [ ] CEO ได้รับ confirmation

---

## SOP-002: Assignment & Delegation

**วัตถุประสงค์:** งานถึงคนถูกต้อง พร้อม resources ที่จำเป็น

**ขั้นตอน:**

1. พิจารณาว่างานนี้:
   - **ประเภทอะไร** — Dev / Design / Research / Operations / Writing
   - **ซับซ้อนแค่ไหน** — ตรงไปตรงมา หรือต้องศึกษา
   - **มีส่วนอิสระที่ทำขนานกันได้ไหม**
2. ถ้าเป็นงานเล็กหรือต่อเนื่องจากเดิม → ทำเอง (default)
3. ถ้าเป็นงานที่มี 2+ ส่วนที่อิสระกันและคุ้มค่า → แตก sub-agent
4. ถ้าเป็นงานที่ต้องศึกษา/ค้น → ใช้ Explore agent
5. สร้างงานย่อย (ถ้ามี) เชื่อม dependency ด้วย `addBlockedBy`

**ข้อควรระวัง:**
- อย่าแตก sub-agent พร่ำเพรื่อ — ค่าเริ่มต้นคือ "ทำเอง"
- แต่ละ sub-agent ต้องได้รับ context เพียงพอที่จะทำงานได้โดยไม่ต้องถามกลับ
- ถ้าใช้ git worktree — ต้อง clean up เมื่อเสร็จ

---

## SOP-003: Execution Guidelines

**วัตถุประสงค์:** ทำงานมีคุณภาพ ตรวจสอบย้อนหลังได้

**ขั้นตอน:**

### 3.1 ก่อนเริ่ม
- ถ้าเป็นโค้ด — สร้าง branch (`feature/ชื่องาน` หรือ `fix/ชื่องาน`)
- ถ้าเป็น content — กำหนด format และ destination path

### 3.2 ระหว่างทำ
- Commit บ่อย — ทุก checkpoint ที่มีความหมาย
- Commit message แบบ conventional: `type(scope): message`
  - `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- อย่าแก้หลายอย่างใน commit เดียว
- อัปเดต task status ด้วย `TaskUpdate — status: in_progress`
- ถ้าติดนานเกิน 30 นาที — สะท้อนปัญหาให้ COO ทราบ

### 3.3 Cleanup
- ปิดทุก service/server/daemon ที่เปิดระหว่างทำงาน
- ลบ temp files
- กรณีทำงานแบบ background agent — รอผลและ clean up

### 3.4 ต้องไม่ทำเด็ดขาด
- ❌ Merge เข้า main โดยไม่ผ่าน Review
- ❌ ทิ้ง process ค้าง
- ❌ ใช้ `--force` push โดยไม่แจ้ง
- ❌ commit credentials หรือ secrets
- ❌ แตก sub-agent โดยไม่จำเป็น

---

## SOP-004: Code Review (เฉพาะงานประเภทโค้ด)

**วัตถุประสงค์:** คุณภาพโค้ด — ไม่มีโค้ดที่ยังไม่ได้ตรวจเข้าสู่ main

**ขั้นตอน:**

1. สร้าง Pull Request พร้อม description
2. ตรวจ:
   - **Logic** — ตรง requirement? edge case ครบ?
   - **Style** — ตรง pattern ของโปรเจค?
   - **Test** — ผ่าน? มีเพิ่มไหม?
   - **Security** — input sanitize? leak?
3. ใช้ `/code-review` (Claude Code) สำหรับ review อัตโนมัติ
4. ใช้ `/security-review` สำหรับงานที่เกี่ยวข้องกับ data/sensitive logic
5. ถ้าพบ issue → comment ใน PR พร้อมเหตุผล
6. เจ้าของโค้ดแก้ → ส่ง review รอบ 2
7. ผ่าน → merge

**SLA การ Review:**
| Priority | ต้อง review ภายใน |
|---|---|
| Urgent | 1 ชม. |
| High | 4 ชม. |
| Medium | 24 ชม. |
| Low | กิจวัตร |

---

## SOP-005: General Review (งานไม่ใช่โค้ด)

**วัตถุประสงค์:** ทุก output มีคุณภาพก่อนส่ง CEO

**ขั้นตอน:**

1. **Self-review** ก่อน — เจ้าของงานตรวจเองก่อน
   - อ่านทวน content
   - ตรวจ spelling/link/format
   - ตรวจว่าตรง requirement
2. **Peer review** (ถ้ามีคนที่สอง)
3. **CEO sign-off** สำหรับงานสำคัญ

**เกณฑ์ผ่าน:**
- [ ] ตรง requirement
- [ ] ไม่มีข้อมูลขาด
- [ ] format อ่านง่าย
- [ ] path/reference ถูกต้อง
- [ ] cleanup เรียบร้อย

---

## SOP-006: Task Completion & Handoff

**วัตถุประสงค์:** ปิดงานให้สะอาด และส่งต่อให้ CEO ทราบ

**ขั้นตอน:**

1. `TaskUpdate — status: completed`
2. ถ้ามี branch → merge to main
3. ถ้ามี worktree → `ExitWorktree — remove`
4. ถ้ามี background process → verify ว่าปิด
5. สรุปผล:
   ```
   ## งานเสร็จ: [ชื่องาน]
   - Priority: [Urgent/High/Medium/Low]
   - สิ่งที่ทำ: (1-2 บรรทัด)
   - สิ่งที่พบ: (bug/decision/tech debt ที่ควรรู้)
   - สิ่งที่ค้าง/แนะนำ: (ถ้ามี)
   ```
6. ถ้ามีอะไรที่ควรจำข้าม session → เขียนลง MEMORY.md หรือ coo.md
7. ส่งสรุปให้ CEO

---

## SOP-007: การจัดการ Blockers

**วัตถุประสงค์:** blocker ต้องถูกสะท้อนและแก้ไขภายในเวลาที่เหมาะสม

**ขั้นตอน:**

1. เมื่อพบ blocker:
   - ตั้ง `TaskUpdate — addBlockedBy` ให้ task ที่เกี่ยวข้อง
   - เขียน comment ว่า blocker คืออะไร
2. ถ้า blocker แก้ได้เอง → แก้
3. ถ้าต้องการตัดสินใจ/approval จาก CEO → ส่ง options พร้อม recommendation
4. ถ้า blocker มีเวลารอนาน → แจ้ง CEO พร้อมผลกระทบ (timeline shift)

---

## SOP-008: มาตรฐานการสื่อสาร

**วัตถุประสงค์:** ทุกคนในออฟฟิศสื่อสารกันรู้เรื่อง

**ข้อปฏิบัติ:**
1. **ตอบรับ** ทุกครั้งที่ถูก Tag — อย่างน้อย acknowledge
2. **กระชับ** — เข้าประเด็น อย่ายืดเยื้อ
3. **กรณีมีปัญหา** — เสนอ options ไม่ใช่แค่บ่น
4. **ภาษาไทย** — ภาษาไทยในการทำงาน (ยกเว้น content ที่ต้องอังกฤษ)
5. **ใช้ SPEAK** — สำหรับประโยคประกาศ/สรุปสั้นๆ ที่เป็นธรรมชาติ
6. **ใช้ SUB** — เฉพาะเมื่อมีงานอิสระหลายส่วนที่ขนานได้จริง

---

## Appendix: คำสั่งลัด

| สถานการณ์ | คำสั่ง |
|---|---|
| เริ่มงาน | `TaskCreate` + `TaskUpdate — in_progress` |
| Review โค้ด | `/code-review` |
| Review ความปลอดภัย | `/security-review` |
| ค้นเอกสารเก่า | `archive-search skill` |
| ประกาศงานเสร็จ | SPEAK + สรุป |

---

*SOP เหล่านี้เป็น living document — ปรับปรุงได้เมื่อ workflow จริงพิสูจน์แล้วว่าควรเปลี่ยน*
