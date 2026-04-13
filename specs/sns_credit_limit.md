# Spec: sns_credit_limit

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_credit_limit` |
| PROGRESS.md task # | 3.3 |
| Phase | 3 |
| Depends on (Odoo modules) | `sale_management`, `account` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#5** (ลูกค้า No Credit → หนี้เสีย) |
| Solution type | Custom Module |
| Needs `/acc-validate`? | **Yes** — มี keyword: `credit`, `ar`, `invoice`, `payment` |

---

## 2. Business Context

**AS-IS:** พนักงานขายสร้าง SO ให้ลูกค้าที่ยังค้างชำระเกินวงเงิน → AR พุ่ง → หนี้เสีย

**TO-BE:**
1. ระบบเก็บ `credit_limit` รายลูกค้า (THB)
2. ตอน confirm SO → รวม outstanding AR + SO ที่ pending + amount ปัจจุบัน ≤ credit_limit
3. ถ้าเกิน → **block** + ปุ่มขอ override จากผู้จัดการ (require reason)
4. Overdue invoice → auto-create `mail.activity` for Accountant + email to partner
5. Dashboard: % credit used per customer

**Workflow:** TO-BE Sales Order Flow ข้อ 2 — "Credit Limit" + AR & Payment Flow ข้อ 5 — "Block SO ใหม่"

---

## 3. Functional Requirements

### 3.1 User stories
- As **Sales Rep**, ฉันต้องการเห็น credit remaining ก่อน confirm SO
- As **Sales Rep**, ถ้าเกิน limit ต้อง block + ขอ override ไม่ใช่เตือนเฉยๆ
- As **Sales Manager**, ฉันต้องการ approve override ด้วยเหตุผลที่บันทึกไว้
- As **Accountant**, ฉันต้องการ follow-up task อัตโนมัติเมื่อ invoice overdue > N วัน

### 3.2 Acceptance criteria

```gherkin
Scenario: SO within limit
  Given ลูกค้า A มี credit_limit 100,000 บาท, outstanding AR 30,000
  When user confirm SO amount 50,000
  Then SO state = sale (30k + 50k = 80k ≤ 100k)

Scenario: SO exceeds limit — blocked
  Given ลูกค้า A มี credit_limit 100,000, outstanding AR 80,000
  When user confirm SO amount 30,000
  Then ระบบ raise UserError + แสดง wizard "Credit Limit Exceeded"
  And SO state = draft

Scenario: Manager override with reason
  Given wizard ขึ้น "Credit Limit Exceeded"
  When sales manager กรอกเหตุผล + Approve Override
  Then SO confirm สำเร็จ
  And chatter: "Credit override by <manager>: <reason> (+<excess> THB over limit)"
  And SO field `credit_override_reason` = reason

Scenario: Non-manager cannot override
  Given sales rep (ไม่ใช่ manager) เห็น wizard
  When rep ลองกรอก reason + submit
  Then raise AccessError — ต้องเป็น sales manager

Scenario: Auto follow-up on overdue
  Given invoice มี due_date < today - 7 days, state=posted, amount_residual>0
  When nightly cron runs
  Then สร้าง mail.activity (type=reminder) on partner for accountant
  And ส่ง email template ถึง partner

Scenario: Credit display
  Given partner form view
  Then เห็น field: credit_limit, outstanding_ar, credit_used_pct, available_credit
```

### 3.3 Out of scope
- ไม่ integrate กับเครดิตบูโร
- ไม่มี credit score (เก็บแค่ limit + used)
- ไม่ block การสร้าง quotation — block แค่ confirm SO
- ไม่ block invoice posting (เฉพาะ SO)
- ไม่ LINE notify (เป็นงานของ `sns_line_notify` Phase 5)

---

## 4. Technical Design

### 4.1 Data model

**Inherit `res.partner`:**
- `credit_limit` — exists already (res.partner มี field นี้ใน account module) — reuse
- `sns_outstanding_ar` — computed, stored, คำนวณจาก `account.move.line` (amount_residual > 0, account_type=asset_receivable)
- `sns_pending_so_amount` — computed, stored, sum ของ SO state=sale, invoiced แล้วแต่ partial + draft ที่ confirm แล้ว
- `sns_credit_used` — outstanding_ar + pending_so
- `sns_credit_used_pct` — computed, percentage
- `sns_credit_available` — credit_limit - credit_used

**Inherit `sale.order`:**
- `sns_credit_override_reason` (Text, tracking=True)
- `sns_credit_override_user_id` (Many2one res.users, tracking=True)
- override `action_confirm()`:
  - ถ้า context `skip_sns_credit_check` → super()
  - คำนวณว่าเกินหรือไม่
  - ถ้าเกิน → return wizard action

**New wizard `sns.credit.override.wizard`** (Transient):
- `order_id` Many2one sale.order
- `partner_credit_limit` Float (readonly, related from partner)
- `partner_outstanding_ar` Float (readonly)
- `order_amount` Float (readonly)
- `exceeds_by` Float (computed)
- `reason` Text (required)
- action `action_approve()` — check user.has_group('sales_team.group_sale_manager') → call super().action_confirm() with skip context

**Cron `cron_sns_credit_followup`** (daily):
- find overdue invoices (due_date < today - threshold)
- create mail.activity on partner + optional email
- threshold: `ir.config_parameter` `sns_credit_limit.followup_days` (default 7)

### 4.2 Business logic

**Outstanding AR computation:**
```python
@api.depends('invoice_ids.amount_residual','invoice_ids.state','invoice_ids.move_type')
def _compute_outstanding_ar(self):
    for partner in self:
        moves = self.env['account.move'].search([
            ('partner_id','=',partner.id),
            ('move_type','in',('out_invoice','out_refund')),
            ('state','=','posted'),
            ('payment_state','in',('not_paid','partial')),
        ])
        partner.sns_outstanding_ar = sum(moves.mapped('amount_residual'))
```

**Credit check on confirm:**
```python
def _sns_check_credit(self):
    self.ensure_one()
    limit = self.partner_id.credit_limit or 0
    if limit <= 0:
        return True  # no limit set = unlimited
    used = self.partner_id.sns_credit_used + self.amount_total
    return used <= limit, used - limit
```

### 4.3 Views

- extend res.partner form → เพิ่ม "Credit Information" tab/group
- extend sale.order form → แสดง credit remaining + warning banner
- wizard form
- tree view ของ partner: filter overdue, sortable by credit_used_pct

### 4.4 Security

`security/ir.model.access.csv`:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sns_credit_override_wizard_sale_user,...,model_sns_credit_override_wizard,sales_team.group_sale_salesman,1,1,1,0
access_sns_credit_override_wizard_manager,...,model_sns_credit_override_wizard,sales_team.group_sale_manager,1,1,1,1
```

**ir.rule:** ไม่ต้องเพิ่ม

**Check ใน wizard:** `action_approve()` ตรวจ `user.has_group('sales_team.group_sale_manager')` → raise AccessError ถ้าไม่ใช่

### 4.5 Reports
N/A

### 4.6 Integrations
- Email template `sns_credit_limit.mail_template_followup`
- Cron runs daily at 08:00

---

## 5. Thai Localization Checklist

- [x] Amount แสดง THB (currency_id ของ company)
- [x] Email template ภาษาไทย (with fallback ถ้าลูกค้าต่างชาติ)
- [x] Activity note ภาษาไทย
- [ ] Tax N/A — แค่ check AR

---

## 6. Test Plan

### 6.1 Unit tests
- `test_credit_within_limit_confirms` — 80k + 20k = 100k = limit → OK
- `test_credit_exceeds_opens_wizard` — 80k + 30k > 100k → wizard
- `test_non_manager_cannot_approve` — rep click approve → AccessError
- `test_manager_override_logs_chatter`
- `test_unlimited_credit` — limit=0 → ไม่ check
- `test_outstanding_ar_computes_correctly` — สร้าง invoice partial paid → AR = residual
- `test_pending_so_excluded_after_invoice` — SO ที่ invoice เต็มแล้ว ไม่นับ pending

### 6.2 Integration / E2E
1. Set partner credit_limit = 10,000
2. สร้าง invoice 3,000 (unpaid)
3. สร้าง SO 8,000 → confirm → ต้อง block (3+8=11 > 10)
4. Manager override → confirm OK
5. Check chatter + partner.sns_outstanding_ar

### 6.3 Security test
- Sales rep cannot approve override (AccessError)
- Partner.credit_limit writable เฉพาะ account_manager + sales_manager

### 6.4 Data scenarios
- Partner ไม่มี credit_limit (= 0) → skip check
- Partner มี invoices อยู่ 100 ใบ → compute performance OK
- SO amount 0 → always passes
- Partner = company เอง (internal) → skip check

---

## 7. Migration Impact
- Legacy data: set credit_limit ตอน migrate customer master (Phase 5.6)
- Outstanding AR: มาจาก opening balance (5.9)

---

## 8. Deployment Notes

- Install: `docker compose exec odoo odoo -d foilss -i sns_credit_limit --stop-after-init`
- Config: Settings → Sales → Credit Limit
  - Follow-up days threshold (default 7)
  - Enable follow-up emails (default True)
- Cron active by default (daily 08:00)

---

## 9. Definition of Done

- [ ] `/biz-validate sns_credit_limit` ผ่าน
- [ ] **`/acc-validate sns_credit_limit` ผ่าน** (มี credit/ar/invoice keyword)
- [ ] `/dev sns_credit_limit` — code + view + security + cron + email template
- [ ] `/qa sns_credit_limit` — review + security + testplan
- [ ] `/verify sns_credit_limit` — end-to-end
- [ ] Update PROGRESS.md 3.3 → ✅ Done
