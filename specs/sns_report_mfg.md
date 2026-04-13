# Spec: sns_report_mfg

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_report_mfg` |
| PROGRESS.md task # | 4.4 |
| Phase | 4 |
| Depends on (Odoo modules) | `mrp` |
| Pain point IDs addressed | **#6** (เอกสารรูปแบบบริษัท), **#9** (ติดตาม BOM cost) |
| Solution type | Custom QWeb Reports |
| Status | **Spec Only — Implementation Deferred** (ต้อง `/ui` mockup) |

---

## 2. Business Context

**AS-IS:** Odoo MO print ใช้ default template ซึ่งไม่ตรงกับใบสั่งผลิตของ foilss.com — ทีมผลิตต้อง copy ไป Excel

**TO-BE:** 3 reports:

| Report | Target | Purpose |
|--------|--------|---------|
| **ใบสั่งผลิต (MO Production Order)** | `mrp.production` | Operator print เพื่อเบิกของ + ลงเครื่องจักร |
| **ใบตรวจวัตถุดิบ (RM Consumption Report)** | `mrp.production` | สรุป RM ที่ใช้จริง vs BOM + variance |
| **ใบสำเร็จ FG (MO Finish Report)** | `mrp.production` | สรุป FG output + scrap + yield % |

---

## 3. Functional Requirements

### 3.1 Acceptance criteria

```gherkin
Scenario: Print ใบสั่งผลิต
  Given MO/2568/00001 qty=1000 ชิ้น
  When click "Print ใบสั่งผลิต"
  Then PDF แสดง:
    - Header: บจก. เอส แอนด์ เอส + logo
    - MO number, date (DD/MM/พ.ศ.)
    - Product + UoM + qty
    - BOM breakdown: RM list + qty ที่ต้องเบิก
    - Work Orders (WO): step + machine + estimated duration
    - Signature: Operator / Supervisor / QC

Scenario: Yield variance warning
  Given MO expected 1000 output, actual 950 (95% yield)
  When generate MO Finish Report
  Then shows yield 95.0% with yellow warning (below 98% threshold)
```

### 3.2 Fields to show
- Doc: `name`, `date_start`, `date_finished`, `state` (Thai labels)
- Product + bom_id + qty_producing + product_qty
- RM lines: `move_raw_ids` → product, expected, consumed, scrap
- FG lines: `move_finished_ids` → product, expected, produced, scrap
- Operator: `user_id`, Work center info

---

## 4. Technical Design

```
addons/sns_report_mfg/
├── __manifest__.py
├── report/
│   ├── mo_production_order.xml   # inherit mrp.report_mrporder
│   ├── mo_rm_consumption.xml     # new report
│   └── mo_finish_report.xml      # new report
└── models/
    └── ir_actions_report.py      # helpers (yield %, Thai date)
```

### 4.1 Helpers
```python
def _compute_yield_pct(self, mo):
    expected = sum(mo.move_finished_ids.filtered(lambda m: m.state != 'cancel').mapped('product_uom_qty'))
    produced = mo.qty_produced or 0
    return (produced / expected * 100) if expected else 0
```

---

## 5. Thai Localization Checklist

- [ ] Thai date (DD/MM/พ.ศ.)
- [ ] State labels: draft=ร่าง, confirmed=ยืนยัน, in_progress=กำลังผลิต, done=เสร็จสิ้น
- [ ] Signature blocks ภาษาไทย (ผู้ผลิต / หัวหน้า / QC)

---

## 6. Definition of Done

- [ ] 3 reports render + print correctly
- [ ] Thai layout verified by production team
- [ ] Yield + scrap calculation tested
- [ ] `/qa` + `/verify` passed
- [ ] PROGRESS.md 4.4 → ✅ Done
