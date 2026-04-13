# Spec: sns_quality_control

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_quality_control` |
| PROGRESS.md task # | 4.5, 4.6, 4.7 |
| Phase | 4 |
| Depends on (Odoo modules) | `stock`, `mrp`, `mail` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#7** (QC ไม่เป็นระบบ — RM เข้าโดยไม่ตรวจ, FG ออกโดยไม่ตรวจ → เจอสินค้าเสียปลายทาง) |
| Solution type | Custom Module (replaces Enterprise `quality_control`) |
| Status | **Spec Only — Implementation Deferred** |

> **Note:** Odoo Community ไม่มี `quality` module (Enterprise-only). โมดูลนี้สร้างขึ้นเพื่อ replace ขั้นต่ำที่ foilss.com ต้องการ — ถ้าลูกค้าซื้อ Enterprise ในอนาคต ให้เปลี่ยนไปใช้ `quality_control` + migrate data

---

## 2. Business Context

**AS-IS:** ไม่มี QC systematic — ทีม QC ใช้สมุดจดมือ → หาย / ไม่ track ได้ → สินค้าเสียปลายทาง

**TO-BE:** 3 QC Check Points ตาม business workflow:

| QC Point | ตำแหน่ง | Trigger | ใครตรวจ |
|----------|---------|---------|---------|
| **Incoming QC** | WH_RM receipt step 2 (QC-wait → Stock) | stock.picking type = in + route = 2-step | QC Inspector |
| **In-Process QC** | ระหว่าง WO (Work Order) | MO Work Order ถึง checkpoint | Production + QC |
| **Outgoing QC** | WH_FG Pack step → Ship step | Pack picking done | QC Inspector |

ถ้า QC Fail → stock.move หยุด + สร้าง `sns.quality.alert` → ทีม QC review → decision (rework / scrap / release with deviation)

---

## 3. Functional Requirements

### 3.1 User stories
- As **QC Inspector**, ฉันต้องการ checklist ตามประเภทสินค้า (ไม่ใช่ generic)
- As **QC Inspector**, ฉันต้องการ log ผล PASS/FAIL + เหตุผล + รูปถ่าย
- As **Warehouse**, ฉันไม่สามารถ validate picking ถ้า QC pending
- As **Production Manager**, ฉันต้องการดู QC report รายวัน (fail rate / common defects)

### 3.2 Acceptance criteria

```gherkin
Scenario: Incoming QC — RM pending
  Given RM shipment arrives at WH_RM, receipt step 1 validated (to QC-wait location)
  Then ระบบสร้าง sns.quality.check (type=incoming) อัตโนมัติ
  And step 2 (QC-wait → Stock) ไม่สามารถ validate ได้จนกว่า check = pass

  When QC Inspector บันทึกผล pass
  Then step 2 unlocked → RM moves to Stock

Scenario: In-Process QC fail creates alert
  Given WO step 3 (Cutting) ถึง QC checkpoint
  When QC ระบุ fail + เหตุผล "size out of spec ±0.5mm"
  Then ระบบสร้าง sns.quality.alert
  And MO state = paused (ต้อง Production Mgr decide)
  And Production Mgr ได้รับ mail.activity

Scenario: Outgoing QC blocks ship
  Given FG packed, Pack picking done
  Then sns.quality.check (type=outgoing) created auto
  And Ship picking ไม่สามารถ start ได้จนกว่า QC pass
```

---

## 4. Technical Design

### 4.1 Models

```python
# sns.quality.checkpoint (configuration — ใครตรวจอะไร เมื่อไหร่)
- name, active, company_id
- trigger_type: selection [('incoming', 'Incoming'), ('in_process', 'In-Process'), ('outgoing', 'Outgoing')]
- product_ids: Many2many  # ใช้กับสินค้าไหน
- product_category_ids: Many2many  # หรือ category
- picking_type_ids: Many2many  # trigger on which picking type
- operation_id: Many2one(mrp.routing.workcenter)  # in-process: which WO step
- inspector_group_id: Many2one(res.groups)
- check_template_ids: One2many(sns.quality.check.template)

# sns.quality.check.template (checklist items)
- checkpoint_id, name (e.g., "ตรวจสี / ตรวจขนาด / ตรวจน้ำหนัก")
- measure_type: selection [('pass_fail', 'Pass/Fail'), ('measure', 'Numeric Measurement'), ('visual', 'Visual')]
- norm_min, norm_max (for measure)
- unit

# sns.quality.check (instance — ผลตรวจจริง)
- checkpoint_id, picking_id, production_id, workorder_id
- lot_id, product_id, qty
- inspector_id, check_date, state: draft/pass/fail
- line_ids: One2many
- notes

# sns.quality.check.line
- check_id, template_id, measure_type
- value_pass_fail, value_measured
- pass_fail (computed), notes

# sns.quality.alert (when fail → action needed)
- check_id, state: new/reviewed/resolved
- severity: low/medium/high
- decision: rework / scrap / release_with_deviation
- resolved_by, resolved_date
```

### 4.2 Blocking logic

```python
# stock.picking.button_validate — override
def button_validate(self):
    self._sns_check_qc_gate()
    return super().button_validate()

def _sns_check_qc_gate(self):
    pending = self.env['sns.quality.check'].search([
        ('picking_id', '=', self.id),
        ('state', '=', 'draft'),
    ])
    if pending:
        raise UserError(_('ไม่สามารถ validate ได้ — มี QC check pending %d รายการ', len(pending)))
```

### 4.3 Files
```
addons/sns_quality_control/
├── models/
│   ├── sns_quality_checkpoint.py
│   ├── sns_quality_check.py
│   ├── sns_quality_alert.py
│   ├── stock_picking.py       # override button_validate
│   └── mrp_workorder.py       # checkpoint hook
├── wizards/
│   └── sns_quality_alert_resolve_wizard.py
├── security/...
├── data/
│   └── mail_template.xml      # QC fail notification
├── report/
│   └── sns_quality_report.xml # daily QC summary
└── views/...
```

---

## 5. Test Plan

1. Incoming: RM arrives → QC check auto-created → step 2 blocked until pass ✓
2. In-process fail → alert + MO paused ✓
3. Outgoing fail → Ship blocked until decision ✓
4. Inspector w/o group cannot validate check ✓
5. Daily QC summary report shows fail rate by product/operator ✓
6. Deviation release requires Production Manager group ✓

---

## 6. Definition of Done

- [ ] All 3 QC points functional + blocking
- [ ] Checklist template engine works for 3 measure types
- [ ] Alert → decision flow tested
- [ ] Daily QC dashboard/report ready
- [ ] `/qa` + `/verify` passed
- [ ] PROGRESS.md 4.5/4.6/4.7 → ✅ Done

> **Future upgrade path:** ถ้าลูกค้าขึ้น Enterprise → migrate ไป `quality_control` native โดย map `sns.quality.check` → `quality.check` field-by-field
