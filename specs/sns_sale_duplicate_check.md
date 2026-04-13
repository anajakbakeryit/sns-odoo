# Spec: sns_sale_duplicate_check

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_sale_duplicate_check` |
| PROGRESS.md task # | 2.3 |
| Phase | 2 |
| Depends on (Odoo modules) | `sale_management` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#3** (คีย์ออเดอร์ซ้ำ) |
| Solution type | Custom Module |
| Needs `/acc-validate`? | No (ไม่มี tax/invoice/accounting keyword) |

---

## 2. Business Context

**AS-IS:** พนักงานขายหรือธุรการสร้าง SO ซ้ำโดยไม่รู้ตัว — ลูกค้าเดียวกัน สินค้าเดียวกัน ช่วงเวลาใกล้กัน → คลังเตรียมของซ้ำ เสียค่าขนส่งเพิ่ม ลูกค้าปฏิเสธรับสินค้าครั้งที่ 2

**TO-BE:** ระบบตรวจจับและเตือนก่อน confirm SO ว่ามีเอกสารใกล้เคียงอยู่แล้ว ให้ user ตัดสินใจว่าจะ proceed, cancel หรือ merge

**Workflow:** TO-BE Sales Order Flow ข้อ 2 — "ระบบตรวจ: Duplicate Check → Credit Limit → Stock Available"

---

## 3. Functional Requirements

### 3.1 User stories
- As a **Sales Rep**, ฉันต้องการให้ระบบเตือนถ้า SO ที่กำลังยืนยันคล้ายกับ SO เก่าของลูกค้าเดียวกัน เพื่อกันการคีย์ซ้ำ
- As a **Sales Manager**, ฉันต้องการ override ได้ถ้าเป็น re-order จริง (ไม่ใช่ duplicate) โดยต้อง log เหตุผล

### 3.2 Acceptance criteria

```gherkin
Scenario: Duplicate detected on confirm
  Given SO เก่าของลูกค้า A มีสินค้า X qty 100 วันที่ D (state=sale)
  And SO ใหม่ของลูกค้า A มีสินค้า X qty 100
  And ช่วงห่าง ≤ 7 วันจาก D
  When user กด Confirm บน SO ใหม่
  Then ระบบแสดง wizard เตือน + list SO ที่ match
  And user ต้องเลือก: Proceed (ระบุเหตุผล) / Cancel / View existing

Scenario: Not duplicate (different product)
  Given SO เก่าลูกค้า A มีสินค้า X
  And SO ใหม่ลูกค้า A มีสินค้า Y (ต่างกัน)
  When user confirm
  Then confirm ปกติ ไม่มี wizard

Scenario: Partial overlap
  Given SO เก่าลูกค้า A มีสินค้า X qty 100, Y qty 50
  And SO ใหม่ลูกค้า A มีสินค้า X qty 100, Z qty 20
  When user confirm
  Then wizard แสดง SO เก่า + highlight เฉพาะ X ที่ overlap

Scenario: Override logged
  Given wizard ขึ้นเตือน duplicate
  When user เลือก Proceed พร้อมเหตุผล "ลูกค้าสั่งเพิ่ม รอบ 2"
  Then SO confirm สำเร็จ
  And chatter บันทึก: "Duplicate override by <user>: <reason> (matched SO/2568/00xxx)"
```

### 3.3 Out of scope
- ไม่ merge SO อัตโนมัติ (ต้องทำมือถ้าจะรวม)
- ไม่ตรวจข้าม company
- ไม่ตรวจกับ quotation (state=draft/sent) — ตรวจเฉพาะ state ∈ {sale, done}
- ไม่มี email alert ให้ผู้จัดการ — เฉพาะ chatter log

---

## 4. Technical Design

### 4.1 Data model

ไม่มี new model — inherit เท่านั้น

**Inherit `sale.order`:**
- method: `action_confirm()` override → เรียก `_check_duplicates()` ก่อน `super()`
- method: `_check_duplicates()` → return matching SO records
- method: `_find_duplicate_domain()` → สร้าง domain สำหรับ search
- field: `duplicate_override_reason` (Text, tracking=True)

**Inherit `res.config.settings`:**
- `duplicate_check_days` (Integer, default=7) — window การตรวจเป็นวัน
- `duplicate_check_enabled` (Boolean, default=True)
- stored ใน `ir.config_parameter`:
  - `sns_sale_duplicate_check.days`
  - `sns_sale_duplicate_check.enabled`

**New wizard `sns.sale.duplicate.wizard`** (Transient):
- `order_id` Many2one sale.order
- `matched_order_ids` Many2many sale.order (readonly)
- `override_reason` Text (required ถ้ากด Proceed)
- action: `action_proceed()` — set reason → call `order.with_context(skip_duplicate=True).action_confirm()`
- action: `action_cancel()` — close wizard, SO stay in draft

### 4.2 Business logic

**Duplicate matching rules:**
- same `partner_id`
- same company
- `date_order` ห่างกัน ≤ `duplicate_check_days` (config, default 7 วัน)
- state ∈ `('sale','done')`
- product overlap: **อย่างน้อย 1 `product_id`** ใน order_line ต้องตรงกัน + qty ใกล้เคียง (±10%)
- exclude SO ปัจจุบัน

**Flow:**
1. user กด Confirm → `action_confirm()` ถูกเรียก
2. ถ้า context มี `skip_duplicate=True` → `super().action_confirm()` (user override แล้ว)
3. ถ้า `duplicate_check_enabled=False` → super()
4. call `_check_duplicates()` → คืน matched orders
5. ถ้า empty → super() ปกติ
6. ถ้าพบ → raise action เปิด wizard `sns.sale.duplicate.wizard`

### 4.3 Views (XML)

- `sns_sale_duplicate_wizard_form` — wizard form: list matched SO + textarea reason + 2 buttons
- extend `res.config.settings` view → เพิ่ม group "Duplicate SO Detection"

### 4.4 Security

`security/ir.model.access.csv`:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sns_sale_duplicate_wizard_user,sns.sale.duplicate.wizard user,model_sns_sale_duplicate_wizard,sales_team.group_sale_salesman,1,1,1,0
```

- ไม่มี record rule เพิ่ม
- override reason log ผ่าน `mail.thread` ของ sale.order

### 4.5 Reports (QWeb)
N/A

### 4.6 Integrations
N/A

---

## 5. Thai Localization Checklist

- [x] N/A — ไม่มี printed document
- [x] ไม่มี tax/VAT/WHT
- chatter messages ใช้ภาษาไทยได้ (จะเป็นสิ่งที่ user อ่าน)

---

## 6. Test Plan

### 6.1 Unit tests (`tests/test_duplicate.py`)
- `test_no_duplicate_proceeds` — SO ที่ไม่ซ้ำ confirm ปกติ
- `test_duplicate_opens_wizard` — SO ซ้ำ → `action_confirm` return wizard action
- `test_override_confirms_with_log` — proceed พร้อม reason → state=sale, chatter มี message
- `test_cancel_keeps_draft` — cancel wizard → state=draft
- `test_window_config` — เปลี่ยน window เป็น 1 วัน → SO ที่ห่าง 3 วันไม่ match
- `test_disabled_bypasses` — `duplicate_check_enabled=False` → ไม่ call check
- `test_qty_tolerance` — qty ต่างกัน 5% → match; ต่างกัน 15% → ไม่ match
- `test_partial_overlap` — มี product ซ้ำ 1 ตัว + product ใหม่ 1 ตัว → match

### 6.2 Integration / E2E
1. Login sales rep → สร้าง SO A (ลูกค้า X, สินค้า P, qty 100) → Confirm
2. สร้าง SO B (ลูกค้า X, สินค้า P, qty 100) → Confirm → wizard ขึ้น
3. View existing → เปิด SO A ดูได้
4. กลับมา SO B → Proceed w/ reason "re-order" → confirm สำเร็จ
5. ตรวจ chatter SO B → เห็น message

### 6.3 Security test
- Sales rep ไม่สามารถ skip wizard ด้วย URL manipulation (context `skip_duplicate=True` ต้องมาจาก wizard only)
- Reason field ต้อง required เมื่อกด Proceed

### 6.4 Data scenarios
- SO เดียวกันที่ตั้งใจ re-order ทุกเดือน (expected override)
- ลูกค้าเดียวกันสั่งสินค้าคนละรุ่น (expected pass)
- ลูกค้าสั่งสินค้าเดียวกันแต่หลายที่อยู่ส่ง (ยัง duplicate — เพราะ partner_id เดียวกัน)

---

## 7. Migration Impact
N/A — new module, no legacy data

---

## 8. Deployment Notes

- Install: Settings → Apps → Update Apps List → install `sns_sale_duplicate_check`
- Config หลัง install: Settings → Sales → Duplicate SO Detection
  - Check days window (default 7)
  - Enabled (default True)

---

## 9. Definition of Done

- [ ] `/biz-validate sns_sale_duplicate_check` ผ่าน
- [x] `/acc-validate` ไม่ต้อง — ไม่มี tax keyword
- [ ] `/dev sns_sale_duplicate_check` — code + view + security
- [ ] `/qa sns_sale_duplicate_check` — review + security + testplan
- [ ] `/verify sns_sale_duplicate_check` — end-to-end
- [ ] Update PROGRESS.md 2.3 → ✅ Done
