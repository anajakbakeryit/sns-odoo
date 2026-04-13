# PROGRESS — Odoo 18 ERP | foilss.com

> อัปเดตไฟล์นี้ทุกครั้งที่ status เปลี่ยน อ่านก่อนทำงานทุกครั้ง

## Status Legend
- ✅ Done | 🔄 In Progress | ⬜ Todo | ❌ Blocked | ⏸ On Hold

## Dependency Notation
`depends: 1.2, 1.3` = task นี้เริ่มได้เมื่อ 1.2 และ 1.3 เสร็จแล้ว (✅)

---

## Phase 1 — Foundation & Core Config

| # | งาน | Status | Depends | หมายเหตุ |
|---|-----|--------|---------|---------|
| 1.1 | Docker Compose + odoo.conf setup | ✅ Done | — | รันที่ port 8069, DB: `foilss` |
| 1.2 | Install `l10n_th` (Thai CoA) | ✅ Done | 1.1 | +78 modules (account, sale, stock, purchase, mrp, hr) |
| 1.3 | Company config (logo, address, TAX ID 13 digits, สาขา) | ✅ Done | 1.1 | บจก. เอส แอนด์ เอส มัลติโปรดักส์, TAX ID 0105555099516, สำนักงานใหญ่ |
| 1.4 | Multi-currency THB + USD + Auto exchange rate | ✅ Done (manual) | 1.2 | THB+USD active; auto BOT rate = Phase 5 (ไม่มีใน Community) |
| 1.5 | VAT 7% + WHT setup (3%, 5%, 1%, 10%) | ✅ Done | 1.2 | l10n_th มี 7%/1%/2%/3%/5% + เพิ่ม WHT 10% Dividend |
| 1.6 | User roles & groups (Sales/WH/ACC/Mgr/Admin) | ✅ Done | 1.1 | ใช้ built-in groups — custom role = Phase 2+ |
| 1.7 | Master Data: Product, Customer, Supplier, UoM | ⏸ On Hold | 1.3, 1.6 | **รอข้อมูลจริง** → ใช้ `/migrate` ตอน Phase 5 |
| 1.8 | Pricelist config | ⏸ On Hold | 1.7 | รอ 1.7 |

**Phase 1 gate:** ทุกข้อต้อง ✅ ก่อนเริ่ม Phase 2 — เรียก `/preflight phase2` เพื่อตรวจ

---

## Phase 2 — Sales + Inventory + Delivery

| # | งาน | Status | Depends | หมายเหตุ |
|---|-----|--------|---------|---------|
| 2.1 | Sales module config (MTS+MTO route) | ✅ Done | — | MTO route active; MTS = default |
| 2.2 | SO Approval workflow (หัวหน้าขาย + ผู้จัดการสำหรับ discount) | ⬜ Todo | 1.6, 2.1 | **Community ไม่มี Approvals app** — ใช้ custom (`sns_sale_approval`) หรือ OCA |
| 2.3 | **[CUSTOM] `sns_sale_duplicate_check`** | ✅ Done (installed, QA pending) | 2.1 | spec: specs/sns_sale_duplicate_check.md — installed, รอ `/qa` + `/verify` |
| 2.4 | Inventory: Multi-Warehouse (RM, FG, QC-wait) | ✅ Done | 1.1 | FG + RM + QCW created |
| 2.5 | Bin Location: ชั้น/แถว/ช่อง | ✅ Done | 2.4 | 8 example bins ใน FG/Stock (A-01-01 → B-02-02) |
| 2.6 | Lot Number Tracking (วันผลิต + Batch) | ✅ Done | 2.4 | default `tracking=lot` สำหรับ product ใหม่ |
| 2.7 | FIFO Removal Strategy (per product category) | ✅ Done | 2.6 | ใช้กับ 8 internal locations (company-wide) |
| 2.8 | 3-Step Delivery Route (Pick > Pack > Ship) | ✅ Done | 2.4 | FG: 3-step out + 3-step in; RM: 2-step in |
| 2.9 | Barcode scanning config + mandatory scan | ⏸ On Hold | 2.6, 2.8 | **Community ไม่มี stock_barcode** — ใส่ใน sns_report_delivery หรือ OCA |
| 2.10 | Putaway Rules + Replenishment | ⏸ On Hold | 2.5 | รอข้อมูล product จริง (1.7) |
| 2.11 | Invoice policy = Delivered Qty | ✅ Done | 2.1, 2.8 | default + updated 28 demo products |
| 2.12 | **[CUSTOM] `sns_report_delivery`** (Pick List+Barcode, Packing Slip+Label, Loading Sheet) | 🔄 Spec Done | 2.8 | spec: specs/sns_report_delivery.md — implementation deferred (ต้อง `/ui` mockup ก่อน) |

**Phase 2 gate:** `/preflight phase3`

---

## Phase 3 — Accounting + Credit + AR

| # | งาน | Status | Depends | หมายเหตุ |
|---|-----|--------|---------|---------|
| 3.1 | Accounting config: AR, AP, GL accounts mapped | ⬜ Todo | 1.2, 1.5 | |
| 3.2 | FIFO Costing (per product category) | ⬜ Todo | 2.7, 3.1 | |
| 3.3 | **[CUSTOM] `sns_credit_limit`** (Block SO + Override approval + Follow-up) | ⬜ Todo | 2.2, 3.1 | spec: specs/sns_credit_limit.md |
| 3.4 | Bank Reconciliation + Auto Matching rules | ⬜ Todo | 3.1 | |
| 3.5 | Customer Portal (แนบสลิป, ตรวจสถานะ) | ⬜ Todo | 3.1, 3.4 | |
| 3.6 | PO Approval workflow (by budget) | ⬜ Todo | 1.6 | |
| 3.7 | **[CUSTOM] `sns_report_sales`** (Quotation, Invoice, PO ตามรูปแบบบริษัท) | ⬜ Todo | 2.1, 3.6 | spec: specs/sns_report_sales.md |
| 3.8 | **[CUSTOM] `sns_thai_tax_report`** (ภ.พ.30, ภ.ง.ด.3/53/50ทวิ) | ⬜ Todo | 1.5, 3.1 | spec: specs/sns_thai_tax_report.md |

**Phase 3 gate:** `/preflight phase4`

---

## Phase 4 — Manufacturing + Quality + HR

| # | งาน | Status | Depends | หมายเหตุ |
|---|-----|--------|---------|---------|
| 4.1 | Manufacturing (MRP) config: BOM, MO | ⬜ Todo | 2.4, 2.6 | |
| 4.2 | Reordering Rules (Min/Max auto PO) | ⬜ Todo | 4.1 | |
| 4.3 | MO Approval workflow | ⬜ Todo | 1.6, 4.1 | |
| 4.4 | **[CUSTOM] `sns_report_mfg`** (MO report ตามรูปแบบบริษัท) | ⬜ Todo | 4.1 | spec: specs/sns_report_mfg.md |
| 4.5 | Quality Control: Incoming QC (วัตถุดิบ) | ⬜ Todo | 2.4, 4.1 | |
| 4.6 | Quality Control: In-Process QC (ระหว่างผลิต) | ⬜ Todo | 4.1, 4.5 | |
| 4.7 | Quality Control: Outgoing QC (ก่อนส่ง) | ⬜ Todo | 2.8, 4.5 | |
| 4.8 | HR module config (ทะเบียนพนักงาน, ลา) | ⬜ Todo | 1.6 | |
| 4.9 | Payroll config (เงินเดือน, OT, ประกันสังคม, WHT) | ⬜ Todo | 4.8, 1.5 | |
| 4.10 | **[CUSTOM] `sns_zkteco`** (Attendance integration) | ⬜ Todo | 4.8 | spec: specs/sns_zkteco.md |
| 4.11 | Recruitment + Appraisal config | ⬜ Todo | 4.8 | |

**Phase 4 gate:** `/preflight phase5`

---

## Phase 5 — Dashboard + Integration + UAT + Go-Live

| # | งาน | Status | Depends | หมายเหตุ |
|---|-----|--------|---------|---------|
| 5.1 | **[CUSTOM] `sns_line_notify`** (LINE Notification) | ⬜ Todo | 2.2, 3.3 | spec: specs/sns_line_notify.md |
| 5.2 | **[CUSTOM] `sns_dashboard`** (Executive Dashboard) | ⬜ Todo | 2.12, 3.3 | spec: specs/sns_dashboard.md |
| 5.3 | CRM module config | ⬜ Todo | 1.7 | |
| 5.4 | Email Marketing config | ⬜ Todo | 5.3 | |
| 5.5 | Website / E-Commerce config (ถ้าต้องการ) | ⬜ Todo | 1.7, 2.1 | optional |
| 5.6 | Data Migration: Customer | ⬜ Todo | 1.7 | `/migrate customer` |
| 5.7 | Data Migration: Supplier | ⬜ Todo | 1.7 | `/migrate supplier` |
| 5.8 | Data Migration: Product + BOM | ⬜ Todo | 1.7, 4.1 | `/migrate product` |
| 5.9 | Data Migration: AR + AP + Opening Balance | ⬜ Todo | 3.1 | `/migrate ar`, `/migrate ap` |
| 5.10 | Data Migration: Stock Balance (per Location+Lot) | ⬜ Todo | 2.4, 2.6 | `/migrate stock` |
| 5.11 | Data Migration: Employees | ⬜ Todo | 4.8 | `/migrate employee` |
| 5.12 | UAT — Sales flow | ⬜ Todo | all phase 2+3 | |
| 5.13 | UAT — Manufacturing flow | ⬜ Todo | all phase 4 | |
| 5.14 | UAT — Accounting + Tax reports | ⬜ Todo | 3.8 | |
| 5.15 | Training (Sales/WH/ACC/HR/Manager) | ⬜ Todo | UAT done | |
| 5.16 | Production deployment setup | ⬜ Todo | UAT done | `/devops production` |
| 5.17 | Go-Live | ⬜ Todo | 5.15, 5.16 | |
| 5.18 | Post-Go-Live Support (1 month) | ⬜ Todo | 5.17 | |
