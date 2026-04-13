# Spec: <module_name>

> กรอกครบทุกหัวข้อก่อนเริ่ม code — ถ้าหัวข้อไหน N/A ให้เขียน "N/A" พร้อมเหตุผล
> Spec นี้จะถูกอ่านโดย: `/biz-validate`, `/acc-validate` (ถ้ามี trigger), `/dev`, `/qa`, `/verify`

---

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_<name>` |
| PROGRESS.md task # | เช่น 2.3 |
| Phase | 1 / 2 / 3 / 4 / 5 |
| Depends on (Odoo modules) | เช่น `sale_management`, `stock`, `account` |
| Depends on (custom) | เช่น `sns_credit_limit` |
| Pain point IDs addressed | เช่น #3, #5 (ดู `project_foilss_painpoints.md`) |
| Solution type | Config only / Custom Module / Config + Custom |
| Needs `/acc-validate`? | Yes / No (Yes ถ้า spec มี invoice/credit/tax/payment/accounting/journal/cost/vat/wht/ar/ap) |

---

## 2. Business Context

**ปัญหาปัจจุบัน (AS-IS):**
<!-- สรุปจาก painpoints / workflows -->

**สิ่งที่ต้องการ (TO-BE):**
<!-- user story สั้นๆ: "ในฐานะ <role> ฉันต้องการ <action> เพื่อ <value>" -->

**Workflow ที่เกี่ยวข้อง:** (อ้าง `project_foilss_workflows.md`)
<!-- เช่น TO-BE Sales Order Flow ข้อ 2-3 -->

---

## 3. Functional Requirements

### 3.1 User stories
- [ ] As a Sales Rep, ฉันต้องการ...
- [ ] As a Manager, ฉันต้องการ...

### 3.2 Acceptance criteria (Gherkin)
```gherkin
Scenario: <happy path>
  Given <initial state>
  When <action>
  Then <expected result>

Scenario: <edge case>
  Given ...
  When ...
  Then ...
```

### 3.3 Out of scope
<!-- ระบุชัดว่าอะไร "ไม่ทำ" ใน spec นี้ เพื่อกัน scope creep -->

---

## 4. Technical Design

### 4.1 Data model
```python
class <Model>(models.Model):
    _name = 'sns.<name>'
    _inherit = 'mail.thread'     # ถ้าต้อง audit trail
    _description = '<description>'

    field_x = fields.Char(required=True)
    # ...
```

**Inherited models:** (ถ้ามี `_inherit` ของ model อื่น)
- `res.partner` — เพิ่ม field `credit_limit_override`
- `sale.order` — เพิ่ม constraint duplicate check

### 4.2 Business logic / ORM methods
<!-- method signature + คำอธิบาย 1-2 บรรทัด -->
- `action_confirm()` — override เพื่อ trigger credit check
- `_compute_outstanding_ar()` — `@api.depends('invoice_ids.amount_residual')`

### 4.3 Views (XML)
- Form view — location/xpath
- List view — field ที่แสดง
- Search view — filter/group by
- Wizard — ถ้ามี

### 4.4 Security
- `ir.model.access.csv` — model x group (read/write/create/unlink)
- `ir.rule` — row-level (ถ้ามี multi-company หรือ ownership)
- Required groups: `base.group_user`, `sales_team.group_sale_manager`, ...

### 4.5 Reports (QWeb) — ถ้ามี
- Template id
- A4 / label size
- ฟิลด์ที่ต้องแสดง (ภาษาไทย, พ.ศ., TAX ID 13 หลัก)

### 4.6 Integrations — ถ้ามี
- External API / queue / cron
- Credentials: `ir.config_parameter` key

---

## 5. Thai Localization Checklist

ตอบทุกข้อที่ applicable:
- [ ] วันที่แสดงเป็น DD/MM/YYYY + พ.ศ. บน printed docs
- [ ] เลขที่เอกสาร: `<PREFIX>/<BE_YEAR>/<RUNNING>` (reset ทุก fiscal year)
- [ ] VAT 7% แยกบรรทัด (output/input tax account แยก)
- [ ] WHT ถูกต้อง (3%/5%/1%/10% ตามประเภท)
- [ ] TAX ID 13 หลัก + สาขา (สำนักงานใหญ่ / สาขาเลขที่) บนใบกำกับภาษี
- [ ] ภ.พ.30 / ภ.ง.ด.3/53/50ทวิ mapping ถูกต้อง (ถ้าเกี่ยว)

---

## 6. Test Plan

### 6.1 Unit tests (`tests/test_<name>.py`)
- `test_<happy_path>` —
- `test_<edge_case>` —

### 6.2 Integration / E2E flow
ทดสอบ flow ทั้งเส้นตาม `project_foilss_workflows.md`:
1. ...
2. ...

### 6.3 Security test
- Lower-privilege user ต้อง**ไม่**สามารถ bypass approval / override
- Record rule ทำงานถูกต้อง (user A มองไม่เห็น data ของ user B)

### 6.4 Data scenarios
- Zero stock / Over credit limit / Duplicate SO / Wrong LOT scan / Expired lot

---

## 7. Migration Impact — ถ้ามี

- ต้อง migrate field จาก legacy? (Express / Excel / CD Organizer)
- `/migrate <type>` mapping
- Rollback plan

---

## 8. Deployment Notes

- Module upgrade order (ถ้ามี dependency ใน `sns_*`)
- `ir.config_parameter` ที่ต้องตั้งหลัง install
- Data migration script (`data/*.xml` หรือ post-install hook)

---

## 9. Definition of Done

ทุกข้อต้อง ✅ ก่อน mark Done ใน PROGRESS.md:
- [ ] `/biz-validate` ผ่าน (workflow ตรง memory)
- [ ] `/acc-validate` ผ่าน (ถ้ามี trigger keyword)
- [ ] `/dev` เสร็จ — code + view + security
- [ ] `/qa` ผ่าน — code review + security + test plan executed
- [ ] `/verify` ผ่าน — end-to-end flow + edge cases + chatter log
- [ ] อัปเดต `PROGRESS.md` → ✅ Done
