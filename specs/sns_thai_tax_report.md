# Spec: sns_thai_tax_report

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_thai_tax_report` |
| PROGRESS.md task # | 3.8 |
| Phase | 3 |
| Depends on (Odoo modules) | `account`, `l10n_th` |
| Depends on (custom) | — (สามารถใช้ stand-alone) |
| Pain point IDs addressed | **#11** (ภาษีไทยครบถ้วน ยื่นกรมสรรพากรได้ทันที), **#12** (รายงานภาษีที่บัญชีต้องทำทุกเดือนใช้เวลา 3 วัน) |
| Solution type | Custom Reports (PDF + XLSX/CSV) |
| Needs `/acc-validate`? | **Yes** — keyword: `vat`, `wht`, `tax` |
| Status | **Spec Only — Implementation Deferred** |

---

## 2. Business Context

**AS-IS:** บัญชีดึงข้อมูลจาก Express → เปิด Excel → pivot mannual → ยื่น ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 / ภ.ง.ด.50ทวิ — ใช้เวลา ~3 วัน/เดือน และมีโอกาส error สูง

**TO-BE:** Generate รายงานภาษีทุกตัว + CSV/XLSX format ตรงกับที่กรมสรรพากรกำหนด (หรือใกล้เคียงมากพอจะ copy-paste ลงระบบ e-Filing ได้)

### Reports to Deliver

| รายงาน | ความถี่ | Source | รูปแบบ |
|-------|--------|--------|--------|
| **ภ.พ.30** (VAT Return) | รายเดือน | Output tax − Input tax | PDF + CSV |
| **รายงานภาษีขาย** (Sales Tax Report) | รายเดือน | `account.move.line` tax_line_id ที่ sign +VAT 7% | PDF + XLSX |
| **รายงานภาษีซื้อ** (Purchase Tax Report) | รายเดือน | `account.move.line` tax_line_id ที่ sign −VAT 7% | PDF + XLSX |
| **ภ.ง.ด.3** (WHT ผู้รับเป็นบุคคลธรรมดา) | รายเดือน | Vendor bills with partner.is_company=False + WHT tax | PDF + CSV |
| **ภ.ง.ด.53** (WHT ผู้รับเป็นนิติบุคคล) | รายเดือน | Vendor bills with partner.is_company=True + WHT tax | PDF + CSV |
| **ภ.ง.ด.50ทวิ** (WHT รายปีรวม) | รายปี | all WHT taxes, group by partner | PDF + XLSX |

---

## 3. Functional Requirements

### 3.1 User stories
- As **Accountant**, ฉันต้องการกดปุ่มเดียวเพื่อ generate รายงาน ภ.พ.30 ของเดือนที่ปิดบัญชี
- As **Accountant**, ฉันต้องการ export CSV ของ ภ.ง.ด.3/53 เพื่อ upload ขึ้น e-Filing ของสรรพากร
- As **CFO**, ฉันต้องการ preview ยอด VAT ก่อนปิดเดือน เพื่อ plan cash flow (output − input)

### 3.2 Acceptance criteria

```gherkin
Scenario: ภ.พ.30 รายเดือน
  Given ใน ปีภาษี 2568 เดือน 3 มี:
    - Output tax (ภาษีขาย) = 150,000 บาท
    - Input tax (ภาษีซื้อ) = 80,000 บาท
  When accountant กด "สร้างรายงาน ภ.พ.30" เลือกเดือน 03/2568
  Then PDF ออกมาแสดง:
    - ชื่อ/ที่อยู่/TAX ID ผู้ประกอบการ
    - ยอดขายรวม, ยอดขายมี VAT, VAT 7% = 150,000
    - ยอดซื้อมี VAT, VAT ซื้อ = 80,000
    - ภาษีที่ต้องชำระ = 70,000
    - รายการ output/input รายใบกำกับภาษี (list)

Scenario: ภ.ง.ด.53 รายเดือน
  Given ใน 03/2568 มี vendor bills ที่หัก WHT:
    - บจก. ABC: ค่าบริการ 3% × 100,000 = 3,000
    - บจก. XYZ: ค่าเช่า 5% × 50,000 = 2,500
  When generate ภ.ง.ด.53
  Then PDF + CSV แสดง partner แต่ละราย + อัตรา WHT + ยอดภาษีหัก + แยกตามประเภทเงินได้
```

### 3.3 Non-functional
- CSV format ต้องใกล้เคียงกับ template ของ e-Filing (กรมสรรพากร) — user provide actual template ช่วงใกล้ implement
- Thai date format ทุกที่ (DD/MM/พ.ศ.)
- เลขประจำตัวผู้เสียภาษี 13 หลัก show as `X-XXXX-XXXXX-XX-X` format

---

## 4. Technical Design

### 4.1 File Structure
```
addons/sns_thai_tax_report/
├── __manifest__.py
├── models/
│   └── tax_report_helpers.py    # format helpers (TAX ID, Thai date, Thai number)
├── wizards/
│   ├── sns_pp30_wizard.py       # ภ.พ.30 generate wizard
│   ├── sns_pnd3_wizard.py       # ภ.ง.ด.3
│   ├── sns_pnd53_wizard.py      # ภ.ง.ด.53
│   └── sns_pnd50_wizard.py      # ภ.ง.ด.50ทวิ (yearly)
├── report/
│   ├── pp30_report.xml          # QWeb template ภ.พ.30
│   ├── sales_tax_report.xml     # รายงานภาษีขาย
│   ├── purchase_tax_report.xml  # รายงานภาษีซื้อ
│   ├── pnd3_report.xml
│   └── pnd53_report.xml
├── data/
│   └── menu.xml                 # Menu: Accounting > Reports > Thai Tax
└── views/
    └── wizard_views.xml
```

### 4.2 Core Queries
```python
# Sales Tax Report
def _get_sales_tax_lines(self, date_from, date_to):
    return self.env['account.move.line'].search([
        ('move_id.state', '=', 'posted'),
        ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
        ('date', '>=', date_from), ('date', '<=', date_to),
        ('tax_line_id.amount', '=', 7.0),  # VAT 7%
    ])

# WHT Report (ภ.ง.ด.3/53 split by partner.is_company)
def _get_wht_lines(self, date_from, date_to, is_company):
    return self.env['account.move.line'].search([
        ('move_id.state', '=', 'posted'),
        ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
        ('move_id.partner_id.is_company', '=', is_company),
        ('tax_line_id.l10n_th_kind_wht', 'in', ('service', 'rent', 'transport', 'dividend')),
        ('date', '>=', date_from), ('date', '<=', date_to),
    ])
```

### 4.3 Export formats
- PDF: QWeb template (A4 landscape for list reports)
- CSV: `ir.actions.report` with report_type='csv' หรือ custom controller ที่ stream CSV
- XLSX: ใช้ `xlsxwriter` (มีใน Odoo image) ผ่าน controller `/report/xlsx/...`

---

## 5. Thai Localization Checklist

- [ ] TAX ID 13 หลัก format `X-XXXX-XXXXX-XX-X`
- [ ] ปี พ.ศ. (ค.ศ. + 543) ในทุกหัวรายงาน
- [ ] ยอดเงินทศนิยม 2 ตำแหน่ง + separator (1,234,567.89)
- [ ] หัวรายงาน/ฟิลด์ ชื่อภาษาไทยตรงกับแบบฟอร์มสรรพากร:
  - "แบบแสดงรายการภาษีมูลค่าเพิ่ม (ภ.พ.30)"
  - "แบบยื่นรายการภาษีเงินได้หัก ณ ที่จ่าย (ภ.ง.ด.3 / ภ.ง.ด.53)"
  - "หนังสือรับรองการหักภาษี ณ ที่จ่าย (50ทวิ)"
- [ ] CSV header rows + encoding UTF-8 BOM (สรรพากร expect)
- [ ] สาขา: "สำนักงานใหญ่" / "สาขา NNNNN"

---

## 6. Test Plan

1. สร้าง test invoice + vendor bill + WHT → run ภ.พ.30 / ภ.ง.ด.3 / ภ.ง.ด.53 → เช็คยอด
2. Edge case: invoice ข้าม fiscal period (ออกปลายเดือน 3, paid ต้นเดือน 4) → ไม่นับซ้ำ
3. Credit note (ใบลดหนี้) → ยอดเป็นลบใน sales tax report
4. Multi-currency invoice (USD) → แปลงเป็น THB ด้วย rate ณ วันที่ออกใบ
5. Partner ที่ไม่มี TAX ID → warning + exclude from report

---

## 7. Definition of Done

- [ ] 6 รายงาน (ภ.พ.30, sales tax, purchase tax, ภ.ง.ด.3, ภ.ง.ด.53, ภ.ง.ด.50ทวิ) render ถูก
- [ ] CSV export ตรง format สรรพากร (confirm กับ accountant)
- [ ] Accountant test flow ทั้งเดือน → ใช้เวลา < 1 ชม. (เทียบกับ 3 วัน AS-IS)
- [ ] `/acc-validate` ผ่าน (ตรวจยอดรวม + WHT rate + encoding)
- [ ] `/qa` + `/verify` ผ่าน
- [ ] PROGRESS.md 3.8 → ✅ Done
