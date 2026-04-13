# Spec: sns_report_sales

## 1. Metadata

| Field | Value |
|-------|-------|
| Module technical name | `sns_report_sales` |
| PROGRESS.md task # | 3.7 |
| Phase | 3 |
| Depends on (Odoo modules) | `sale_management`, `account`, `purchase` |
| Depends on (custom) | — |
| Pain point IDs addressed | **#6** (เอกสารใช้รูปแบบของ Odoo ไม่ใช่ของบริษัท), **#11** (ใบกำกับภาษีต้องถูกต้องตามกรมสรรพากร) |
| Solution type | Custom QWeb Reports |
| Needs `/acc-validate`? | **Yes** — keyword: `invoice`, `vat`, `tax` |
| Status | **Spec Only — Implementation Deferred** (ต้อง `/ui` mockup ก่อน) |

---

## 2. Business Context

**AS-IS:** ออก Quotation / Invoice / PO ด้วย template ของ Odoo ซึ่งไม่ตรงกับที่บริษัทใช้ในปัจจุบัน (Express, Excel) → ลูกค้า/Supplier ปฏิเสธ, ทีมต้องพิมพ์ใหม่จากไฟล์ Word

**TO-BE:** 3 เอกสารหลัก (Quotation / Invoice / PO) พิมพ์ตรงแบบที่ foilss.com ใช้อยู่:
- A4 portrait
- Logo + ชื่อ+ที่อยู่บริษัท (TAX ID, สาขา) ตามรูปแบบใบกำกับภาษีเต็มรูปแบบ (สรรพากร)
- เลขที่เอกสาร format `<PREFIX>/<BE_YEAR>/<RUNNING>` (เช่น `QT/2568/00001`, `INV/2568/00001`, `PO/2568/00001`)
- วันที่ show **DD/MM/YYYY พ.ศ.**
- ตารางรายการ: รหัส, ชื่อสินค้า (รองรับไทย), UoM, ราคา/หน่วย, ส่วนลด%, รวม
- VAT 7% แยกบรรทัด + ราคาไม่รวม VAT + รวมทั้งสิ้น (แสดงเป็นตัวอักษรไทย "หนึ่งพันห้าร้อยบาทถ้วน")
- WHT note (ถ้ามี): "ผู้จ่ายหัก ณ ที่จ่าย 1% = XXX"
- เงื่อนไขการชำระเงิน, Signature blocks

**Workflow:** referenced in TO-BE Sales Flow step 6 (print quotation), step 10 (print invoice)

---

## 3. Functional Requirements

### 3.1 Reports to Deliver
| Report | Target Model | Trigger |
|--------|-------------|---------|
| **Quotation / Sales Order** | `sale.order` | Print button on SO (state draft/sent/sale) |
| **Tax Invoice / ใบกำกับภาษี** | `account.move` (out_invoice) | Print button on posted customer invoice |
| **Purchase Order** | `purchase.order` | Print button on PO (state purchase/done) |

### 3.2 Acceptance criteria

```gherkin
Scenario: Print Thai Tax Invoice
  Given customer invoice INV/2568/00001 posted, 100,000 THB + VAT 7,000 = 107,000
  When user clicks "Print"
  Then PDF output shows:
    - Header: บจก. เอส แอนด์ เอส มัลติโปรดักส์ | TAX ID 0105555099516 | สำนักงานใหญ่
    - Doc type: "ใบกำกับภาษี / ใบแจ้งหนี้"
    - Date: DD/MM/2568
    - Amount before VAT: 100,000.00 THB
    - VAT 7%: 7,000.00 THB
    - Grand total: 107,000.00 THB
    - Amount in Thai words: "หนึ่งแสนเจ็ดพันบาทถ้วน"
    - Signature blocks: ผู้รับเงิน / ผู้อนุมัติ

Scenario: Quotation with WHT note
  Given quotation with freight line (subject to 1% WHT)
  When user prints quotation
  Then footer shows "หัก ณ ที่จ่าย 1% จากค่าบริการขนส่ง"
```

### 3.3 Non-functional
- Print output must match provided company template (ต้อง `/ui` layout mockup ก่อน implement)
- Thai font rendering (Sarabun / TH SarabunPSK) — verify wkhtmltopdf supports
- Number-to-Thai-text: ใช้ `num2words` library (lang='th') หรือ custom helper

---

## 4. Technical Design

### 4.1 File Structure
```
addons/sns_report_sales/
├── __manifest__.py
├── report/
│   ├── sale_order_report.xml       # inherit sale.report_saleorder_document
│   ├── account_move_report.xml     # inherit account.report_invoice_document
│   └── purchase_order_report.xml   # inherit purchase.report_purchaseorder_document
├── models/
│   └── ir_actions_report.py        # helper: _format_thai_date, _num_to_thai_text
└── static/src/scss/
    └── report.scss                 # Thai font + custom layout
```

### 4.2 Key helpers
```python
# models/ir_actions_report.py
def _format_thai_date(self, d):
    """2026-04-13 → '13/04/2569'"""
    return f"{d.day:02d}/{d.month:02d}/{d.year + 543}"

def _amount_to_thai_text(self, amount):
    """107000.00 → 'หนึ่งแสนเจ็ดพันบาทถ้วน'"""
    # ใช้ num2words(amount, lang='th') + append 'บาทถ้วน' / 'บาทxxสตางค์'
```

### 4.3 Document numbering
- ไม่ต้อง override `ir.sequence` — ใช้ prefix ที่ sequence ปัจจุบันสร้างอยู่แล้ว
- หาก Odoo ใช้ `SO/2026/00001` ต้องเปลี่ยน prefix → use sequence field `prefix = %(range_year)s` แต่ Odoo 18 ใช้ ค.ศ. — ต้อง custom `_get_prefix_suffix`

---

## 5. Thai Localization Checklist

- [ ] Company TAX ID 13 หลัก แสดงใน header
- [ ] สาขา: "สำนักงานใหญ่" หรือ "สาขาเลขที่ NNNNN"
- [ ] ปี พ.ศ. ทุกที่ที่มีวันที่
- [ ] เลขที่เอกสาร format `<PREFIX>/<BE_YEAR>/<RUNNING>`
- [ ] VAT แยกบรรทัด + แสดง rate
- [ ] "ใบกำกับภาษี" heading ตามที่สรรพากรกำหนด (ไม่ใช่ "Invoice")
- [ ] ยอดเงินเป็นตัวอักษรไทย
- [ ] WHT footer note (ถ้ามีรายการบริการ)

---

## 6. Test Plan

1. Print SO draft → no "Tax Invoice" wording, just "ใบเสนอราคา"
2. Print posted invoice → "ใบกำกับภาษี/ใบแจ้งหนี้" header
3. Print credit note → "ใบลดหนี้"
4. Print with multi-line items including discount → table width correct
5. Print PO → "ใบสั่งซื้อ" header + supplier info correct

---

## 7. Definition of Done

- [ ] 3 QWeb templates rendered correctly (QT/INV/PO)
- [ ] Thai date + Thai number-to-text working
- [ ] Print output reviewed + signed off by accountant
- [ ] Edge cases tested (discount, multi-line, no VAT product)
- [ ] `/qa` + `/verify` passed
- [ ] PROGRESS.md 3.7 → ✅ Done
