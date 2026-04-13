# Spec: sns_mo_approval

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_mo_approval` |
| PROGRESS.md task # | 4.3 |
| Phase | 4 |
| Depends on (Odoo modules) | `mrp`, `mail` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#8** (ผลิตมั่วไม่มีขั้นตอนอนุมัติ → ของเกิน/ขาด) |
| Solution type | Custom Module |
| Status | **Spec Only — Implementation Deferred** |

---

## 2. Business Context

**AS-IS:** พนักงานผลิตสร้าง MO แล้วเริ่มงานเลย — ไม่มีขั้น review → บางครั้งผลิตเกิน forecast หรือใช้วัตถุดิบผิด batch

**TO-BE:** MO confirmation ต้องผ่าน approval 1 ชั้น (Production Manager) ก่อน state → `confirmed` และต้องผ่าน approval 2 ชั้น (MD) หาก:
- qty > threshold (default 10,000 ชิ้น) **หรือ**
- ใช้ RM cost > 100,000 THB

---

## 3. Functional Requirements

### 3.1 User stories
- As **Production Operator**, ฉันต้องการ submit MO ไป review (แทน confirm เลย)
- As **Production Manager**, ฉันต้องการ approve MO หรือ reject พร้อมเหตุผล
- As **MD**, ฉันต้องการ approve MO ยอดใหญ่ (>threshold) — low priority MO ผ่าน manager ก็พอ
- As **Production Operator**, ฉันต้องการเห็น status (waiting mgr / waiting MD / approved / rejected)

### 3.2 Acceptance criteria

```gherkin
Scenario: Small MO — single approval
  Given MO qty=500 ชิ้น, RM cost=30,000 THB
  When Operator กด "Submit for Approval"
  Then MO state = 'waiting_manager', Production Manager ได้รับ activity

  When Manager กด Approve
  Then MO state → 'confirmed' (ตาม Odoo standard)

Scenario: Large MO — double approval
  Given MO qty=15,000 ชิ้น
  When Operator submit
  Then MO state = 'waiting_manager'

  When Manager approve
  Then MO state = 'waiting_md', MD ได้รับ activity

  When MD approve
  Then MO state → 'confirmed'

Scenario: Rejection logs reason to chatter
  Given MO waiting_manager
  When Manager กด Reject + กรอก reason
  Then MO state = 'rejected', chatter แสดง "Rejected by <user>: <reason>"
```

---

## 4. Technical Design

### 4.1 State Machine Extension
เพิ่ม state ใหม่บน `mrp.production`:
- `draft` → [Submit] → `waiting_manager`
- `waiting_manager` → [Manager Approve, small] → `confirmed`
- `waiting_manager` → [Manager Approve, large] → `waiting_md`
- `waiting_md` → [MD Approve] → `confirmed`
- any → [Reject] → `rejected`

### 4.2 Files
```
addons/sns_mo_approval/
├── __manifest__.py
├── models/
│   ├── mrp_production.py        # extend state, add approval fields + action methods
│   └── res_config_settings.py   # threshold settings
├── wizards/
│   └── sns_mo_reject_wizard.py  # rejection reason wizard
├── security/
│   ├── ir.model.access.csv
│   └── security.xml             # group_sns_mo_md (MD approver)
└── views/
    ├── mrp_production_views.xml
    └── res_config_settings_views.xml
```

### 4.3 Config parameters
- `sns_mo_approval.qty_threshold` (float, default 10000)
- `sns_mo_approval.cost_threshold` (float, default 100000)

---

## 5. Test Plan

1. Small MO: draft → submit → manager approve → confirmed ✓
2. Large MO qty: requires MD approval ✓
3. Large MO cost: requires MD approval ✓
4. Reject at any stage logs to chatter ✓
5. Non-manager user cannot approve (AccessError) ✓
6. MD can override manager rejection ✓

---

## 6. Definition of Done

- [ ] State machine correct (5 new states)
- [ ] Both thresholds tested
- [ ] Reject wizard + chatter audit
- [ ] Group `sns_mo_md` created + assigned
- [ ] `/qa` + `/verify` passed
- [ ] PROGRESS.md 4.3 → ✅ Done
