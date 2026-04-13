# Spec: sns_report_delivery

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_report_delivery` |
| PROGRESS.md task # | 2.12 |
| Phase | 2 |
| Depends on (Odoo modules) | `stock`, `sale_stock`, `web` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#6** (คลังหยิบผิด), **#8** (หยิบผิด LOT), **#10** (โหลดไม่ครบ) |
| Solution type | Custom Module (Config + Custom per painpoints) |
| Needs `/acc-validate`? | No (ไม่มี tax/invoice — เป็น delivery doc) |

---

## 2. Business Context

**AS-IS:** Pick list เขียนมือ / ไม่มี barcode / พนักงานสแกนไม่ได้ → หยิบผิด lot, โหลดขึ้นรถไม่ครบ, เสียเวลาตรวจซ้ำ

**TO-BE:** 3 รายงานที่พิมพ์จากระบบ + barcode ทุกใบ ให้พนักงานสแกนแทนอ่าน:
1. **Pick List** (ใช้ที่ Pick step) — list สินค้า + bin location + Lot + barcode per line
2. **Packing Slip + Label** (ใช้ที่ Pack step) — รายการลง packaging + sticker ติดลังพร้อม barcode
3. **Loading Sheet** (ใช้ที่ Ship step) — สรุปจำนวนลังขึ้นรถ + barcode รวม

**Workflow:** TO-BE Delivery Flow — Pick > Pack > Ship (3 steps บังคับ)

---

## 3. Functional Requirements

### 3.1 User stories
- As **Warehouse staff (Picker)**, ฉันต้องการ Pick List ที่มี barcode ทุก line → สแกน LOT แทนพิมพ์
- As **Checker (Pack step)**, ฉันต้องการ Packing Slip + sticker ลังแต่ละใบ → ติดลังและเซ็นยืนยัน
- As **Shipping coordinator**, ฉันต้องการ Loading Sheet 1 ใบ → ตรวจจำนวนลังขึ้นรถให้ครบ
- As **Customer**, ฉันต้องการเอกสารส่งมอบที่อ่านง่าย (เลขที่ + วันที่ + รายการ)

### 3.2 Acceptance criteria

```gherkin
Scenario: Pick List printed with barcodes
  Given SO ถูก confirm และ 3-step delivery สร้าง Pick transfer
  When user กด Print → Pick List
  Then QWeb PDF แสดง:
    - Header: ชื่อบริษัท + TAX ID + เลขที่ Pick (format SO/2568/00xxx-P)
    - Body: product + qty + bin location + lot + Code128 barcode per line
    - Footer: พนักงานหยิบ ____ / ผู้ตรวจ ____ / วันที่ DD/MM/พ.ศ.

Scenario: Packing Slip with one label per package
  Given Pack transfer มี 3 packages (ลัง)
  When user print → Packing Slip
  Then 1 หน้า = 1 ลัง แสดง: เลขลัง, SO, partner, รายการในลัง, barcode

Scenario: Loading Sheet summary
  Given Ship transfer มี 15 packages รวม
  When user print → Loading Sheet
  Then 1 หน้าสรุป: driver, truck plate (input field), total packages 15,
       checkbox ทีละลัง + barcode รวม 1 อัน ของ transfer
```

### 3.3 Out of scope
- ไม่มี electronic signature (POD) — save PDF attachment หลัง sign มือ (Phase 3 customer portal ทำ)
- ไม่ integrate กับเครื่อง barcode printer โดยตรง — ใช้ PDF + printer ปกติ
- ไม่ wireless scanner app — ใช้ USB HID scanner (Phase 2.9)

---

## 4. Technical Design

### 4.1 Data model

ไม่มี new model — เพิ่ม fields + reports

**Inherit `stock.picking`:**
- field: `sns_barcode` (Char, computed, store=False) — encode picking.name เป็น Code128
- field: `sns_truck_plate` (Char) — สำหรับ Loading Sheet (ship type เท่านั้น)
- field: `sns_driver_name` (Char)
- method: `_compute_sns_barcode()` — trivial, return self.name

**Inherit `stock.quant.package`:**
- field: `sns_package_barcode` — encode package.name
- method: print label (`action_print_sns_label()`)

### 4.2 Business logic
- ทุก pick/pack/ship ได้ report button เพิ่มใน print menu
- Loading Sheet เฉพาะ `picking_type_code == 'outgoing'` และ `picking_type_id.sequence_code` ตรงกับ ship step
- Auto-number format: `<PREFIX>/<BE_YEAR>/<RUNNING>` — ใช้ ir.sequence ที่ config ไว้ใน Phase 1

### 4.3 Views (XML)

**reports:**
- `sns_report_pick_list` — QWeb template, A4 portrait
- `sns_report_packing_slip` — QWeb, A4 portrait, page break per package
- `sns_report_loading_sheet` — QWeb, A4 portrait
- `sns_report_package_label` — QWeb, 100x150mm sticker

**actions:** `ir.actions.report` 4 records — register ใน print menu ของ stock.picking + stock.quant.package

**barcode helper:** ใช้ Odoo built-in `/report/barcode/Code128/<value>` — ไม่ต้องเขียนเอง

### 4.4 Security
- สืบทอดจาก `stock.group_stock_user` (read picking + print report)
- Loading Sheet fields (truck plate, driver) — editable by `stock.group_stock_manager`

`security/ir.model.access.csv` — ไม่ต้องเพิ่ม (ใช้ stock access เดิม)

**Record rule:** truck_plate, driver_name สามารถแก้ได้เฉพาะ state != done (ป้องกันแก้หลังส่งแล้ว)

### 4.5 Reports (QWeb) — Thai Localization

ทุก report ต้องแสดง:
- [x] Company header: ชื่อบริษัท + ที่อยู่ + โทร + TAX ID 13 หลัก + สาขา
- [x] Document ID: format `<PREFIX>/<BE_YEAR>/<RUNNING>`
- [x] Date: DD/MM/YYYY + พ.ศ. (convert ใน template)
- [x] Barcode: Code128 จาก Odoo built-in route
- [x] Signature lines: ผู้หยิบ / ผู้ตรวจ / ผู้รับ (ตามประเภท)

### 4.6 Integrations
- Odoo `/report/barcode/Code128/{value}` — built-in, no external dep
- USB HID barcode scanner — user-side, no module code

---

## 5. Thai Localization Checklist

- [x] วันที่ DD/MM/YYYY + พ.ศ. — ใช้ helper function ใน QWeb: `{{ (doc.scheduled_date.year + 543) }}`
- [x] เลขที่เอกสาร — ใช้ ir.sequence config format `<PREFIX>/%(year_be)s/%(range_year)05d`
- [x] TAX ID 13 หลัก + สาขา — แสดงใน company header block (shared partial)
- [x] VAT N/A — delivery doc ไม่ใช่ tax invoice

---

## 6. Test Plan

### 6.1 Unit tests
- `test_pick_list_renders` — สร้าง SO → confirm → validate Pick → render PDF ได้ไม่ error
- `test_barcode_value_matches_name` — `sns_barcode == picking.name`
- `test_packing_slip_one_page_per_package` — 3 packages → PDF 3 หน้า
- `test_loading_sheet_only_on_ship` — ห้าม render บน pick/pack
- `test_truck_plate_readonly_after_done` — ไม่สามารถ write หลัง state=done

### 6.2 Integration / E2E
1. SO → Confirm → Pick created
2. Print Pick List → ดู PDF: barcode scannable ด้วย USB scanner (manual test)
3. Validate Pick → Pack created → Print Packing Slip
4. Pack with 3 packages → PDF 3 pages
5. Validate Pack → Ship created
6. Fill truck plate + driver → Print Loading Sheet
7. Validate Ship → invoice eligible

### 6.3 Security test
- Non-stock user: cannot print pick list
- stock_user: can print but cannot edit truck_plate
- stock_manager: can edit truck_plate

### 6.4 Data scenarios
- Delivery with 100 lines → PDF handles multi-page header repeat
- Product name ภาษาไทย + emoji → render ได้ (font embedding)
- Barcode with long picking name (>30 chars) → Code128 OK

---

## 7. Migration Impact
N/A — new reports only

---

## 8. Deployment Notes

- Install: `docker compose exec odoo odoo -d foilss -i sns_report_delivery --stop-after-init`
- Config sequence `<PREFIX>/<BE_YEAR>/<RUNNING>` ต้องตั้งใน ir.sequence สำหรับ picking_type ก่อน Phase 2.12 → ใส่ใน data/ir_sequence.xml
- Test barcode scan ต้องทำกับ printer จริง + scanner จริง

---

## 9. Definition of Done

- [ ] `/biz-validate sns_report_delivery` ผ่าน
- [x] `/acc-validate` ไม่ต้อง (ไม่ใช่ tax doc)
- [ ] `/ui sns_report_delivery` — mockup 3 reports + label
- [ ] `/dev sns_report_delivery` — code + QWeb templates + sequences
- [ ] `/qa sns_report_delivery` — review + security + testplan
- [ ] `/verify sns_report_delivery` — PDF renders + barcode scannable (manual)
- [ ] Update PROGRESS.md 2.12 → ✅ Done

**Implementation deferred to next session** — ต้องทำ UI mockup (`/ui`) ก่อน เพราะ report layout มีรายละเอียดมาก
